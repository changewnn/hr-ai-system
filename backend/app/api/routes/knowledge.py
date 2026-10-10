from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeIndexJob,
    KnowledgeJobStatus,
    KnowledgeVersionStatus,
)
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.audit import record_audit
from app.services.knowledge import (
    prepare_upload,
    process_knowledge_version,
    save_upload,
    search_chunks,
)

router = APIRouter(prefix="/admin/knowledge", tags=["knowledge"])


def _validate_dates(effective_from: date | None, effective_to: date | None) -> None:
    if effective_from and effective_to and effective_to < effective_from:
        raise BusinessError(
            60106, "KNOWLEDGE_EFFECTIVE_DATE_INVALID", "失效日期不能早于生效日期", 422
        )


def _upload_error(exc: ValueError) -> BusinessError:
    messages = {
        "UNSUPPORTED_TYPE": (
            60101,
            "KNOWLEDGE_FILE_UNSUPPORTED",
            "仅支持 PDF、DOCX、MD、TXT 文件",
            415,
        ),
        "UNSUPPORTED_MIME": (60101, "KNOWLEDGE_FILE_UNSUPPORTED", "文件类型与扩展名不匹配", 415),
        "INVALID_SIGNATURE": (60101, "KNOWLEDGE_FILE_UNSUPPORTED", "文件内容与扩展名不匹配", 415),
        "FILE_SIZE": (60102, "KNOWLEDGE_FILE_TOO_LARGE", "文件为空或超过大小限制", 413),
    }
    return BusinessError(
        *messages.get(str(exc), (60103, "KNOWLEDGE_UPLOAD_FAILED", "文件校验失败", 422))
    )


def _version_dict(row: KnowledgeDocumentVersion, chunk_count: int = 0) -> dict:
    return {
        "id": row.id,
        "document_id": row.document_id,
        "version": row.version,
        "status": row.status.value,
        "original_filename": row.original_filename,
        "mime_type": row.mime_type,
        "file_size": row.file_size,
        "checksum": row.checksum,
        "effective_from": row.effective_from,
        "effective_to": row.effective_to,
        "failure_reason": row.failure_reason,
        "published_at": row.published_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "chunk_count": chunk_count,
    }


async def _create_version(
    *,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    current_user_id: int,
    document: KnowledgeDocument,
    version: str,
    effective_from: date | None,
    effective_to: date | None,
    upload: UploadFile,
) -> KnowledgeDocumentVersion:
    _validate_dates(effective_from, effective_to)
    content = await upload.read()
    try:
        prepared = prepare_upload(upload.filename, upload.content_type, content)
    except ValueError as exc:
        raise _upload_error(exc) from exc
    duplicate_version = await session.scalar(
        select(KnowledgeDocumentVersion.id).where(
            KnowledgeDocumentVersion.document_id == document.id,
            KnowledgeDocumentVersion.version == version.strip(),
        )
    )
    if duplicate_version is not None:
        raise BusinessError(60106, "KNOWLEDGE_VERSION_CONFLICT", "该版本号已存在", 409)
    duplicate_file = await session.scalar(
        select(KnowledgeDocumentVersion.id).where(
            KnowledgeDocumentVersion.document_id == document.id,
            KnowledgeDocumentVersion.checksum == prepared.checksum,
        )
    )
    if duplicate_file is not None:
        raise BusinessError(60107, "KNOWLEDGE_FILE_DUPLICATE", "该文档内容已上传", 409)
    try:
        storage_path = save_upload(prepared)
    except OSError as exc:
        raise BusinessError(60103, "KNOWLEDGE_STORAGE_FAILED", "政策文件保存失败", 500) from exc
    row = KnowledgeDocumentVersion(
        document_id=document.id,
        version=version.strip(),
        status=KnowledgeVersionStatus.UPLOADED,
        original_filename=prepared.original_filename,
        storage_path=storage_path,
        mime_type=prepared.mime_type,
        file_size=len(prepared.content),
        checksum=prepared.checksum,
        effective_from=effective_from,
        effective_to=effective_to,
        created_by=current_user_id,
    )
    session.add(row)
    await session.flush()
    job = KnowledgeIndexJob(version_id=row.id, status=KnowledgeJobStatus.PENDING, attempt=1)
    session.add(job)
    await session.flush()
    await record_audit(
        session,
        actor_user_id=current_user_id,
        action="KNOWLEDGE_VERSION_UPLOAD",
        resource_type="knowledge_document_version",
        resource_id=str(row.id),
        after={
            "document_id": document.id,
            "version": row.version,
            "filename": row.original_filename,
        },
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessError(
            60106, "KNOWLEDGE_VERSION_CONFLICT", "版本号或文件内容已存在", 409
        ) from exc
    background_tasks.add_task(process_knowledge_version, row.id, job.id)
    return row


@router.get("")
async def list_documents(
    _: AdminUser,
    session: AsyncSession = Depends(get_db),
    keyword: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    conditions = []
    if keyword:
        conditions.append(KnowledgeDocument.name.ilike(f"%{keyword.strip()}%"))
    if category:
        conditions.append(KnowledgeDocument.category == category)
    total = await session.scalar(
        select(func.count()).select_from(KnowledgeDocument).where(*conditions)
    )
    documents = (
        await session.scalars(
            select(KnowledgeDocument)
            .where(*conditions)
            .order_by(KnowledgeDocument.updated_at.desc(), KnowledgeDocument.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = []
    for document in documents:
        versions = (
            await session.scalars(
                select(KnowledgeDocumentVersion)
                .where(KnowledgeDocumentVersion.document_id == document.id)
                .order_by(KnowledgeDocumentVersion.created_at.desc())
            )
        ).all()
        current = next(
            (item for item in versions if item.status == KnowledgeVersionStatus.PUBLISHED), None
        )
        latest = versions[0] if versions else None
        items.append(
            {
                "id": document.id,
                "name": document.name,
                "category": document.category,
                "description": document.description,
                "version_count": len(versions),
                "current_version": current.version if current else None,
                "latest_status": latest.status.value if latest else None,
                "updated_at": document.updated_at,
            }
        )
    return success({"items": items, "page": page, "page_size": page_size, "total": total or 0})


@router.post("")
async def create_document(
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    session: AsyncSession = Depends(get_db),
    name: str = Form(min_length=1, max_length=200),
    version: str = Form(min_length=1, max_length=50),
    category: str | None = Form(default=None, max_length=100),
    description: str | None = Form(default=None, max_length=2000),
    effective_from: date | None = Form(default=None),
    effective_to: date | None = Form(default=None),
    file: UploadFile = File(...),
) -> dict:
    clean_name = name.strip()
    if await session.scalar(
        select(KnowledgeDocument.id).where(KnowledgeDocument.name == clean_name)
    ):
        raise BusinessError(60106, "KNOWLEDGE_DOCUMENT_EXISTS", "政策文档名称已存在", 409)
    document = KnowledgeDocument(
        name=clean_name,
        category=category.strip() if category else None,
        description=description.strip() if description else None,
        created_by=current_user.id,
    )
    session.add(document)
    await session.flush()
    row = await _create_version(
        session=session,
        background_tasks=background_tasks,
        current_user_id=current_user.id,
        document=document,
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        upload=file,
    )
    return success(
        {"id": document.id, "version_id": row.id}, message="政策文档已上传，正在建立索引"
    )


@router.post("/search")
async def test_search(payload: KnowledgeSearchRequest, _: AdminUser) -> dict:
    try:
        rows = await search_chunks(payload.query.strip(), payload.version_id, payload.limit)
    except RuntimeError as exc:
        raise BusinessError(60103, "KNOWLEDGE_EMBEDDING_FAILED", str(exc), 503) from exc
    return success(rows)


@router.get("/{document_id}")
async def get_document(
    document_id: int, _: AdminUser, session: AsyncSession = Depends(get_db)
) -> dict:
    document = await session.get(KnowledgeDocument, document_id)
    if document is None:
        raise BusinessError(60104, "KNOWLEDGE_DOCUMENT_NOT_FOUND", "政策文档不存在", 404)
    versions = (
        await session.scalars(
            select(KnowledgeDocumentVersion)
            .where(KnowledgeDocumentVersion.document_id == document_id)
            .order_by(KnowledgeDocumentVersion.created_at.desc())
        )
    ).all()
    version_items = []
    for version in versions:
        chunk_count = await session.scalar(
            select(func.count())
            .select_from(KnowledgeChunk)
            .where(KnowledgeChunk.version_id == version.id)
        )
        latest_job = await session.scalar(
            select(KnowledgeIndexJob)
            .where(KnowledgeIndexJob.version_id == version.id)
            .order_by(KnowledgeIndexJob.id.desc())
            .limit(1)
        )
        item = _version_dict(version, chunk_count or 0)
        item["job"] = (
            {
                "id": latest_job.id,
                "status": latest_job.status.value,
                "attempt": latest_job.attempt,
                "error_message": latest_job.error_message,
                "started_at": latest_job.started_at,
                "finished_at": latest_job.finished_at,
            }
            if latest_job
            else None
        )
        version_items.append(item)
    return success(
        {
            "id": document.id,
            "name": document.name,
            "category": document.category,
            "description": document.description,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "versions": version_items,
        }
    )


@router.post("/{document_id}/versions")
async def upload_version(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    session: AsyncSession = Depends(get_db),
    version: str = Form(min_length=1, max_length=50),
    effective_from: date | None = Form(default=None),
    effective_to: date | None = Form(default=None),
    file: UploadFile = File(...),
) -> dict:
    document = await session.get(KnowledgeDocument, document_id)
    if document is None:
        raise BusinessError(60104, "KNOWLEDGE_DOCUMENT_NOT_FOUND", "政策文档不存在", 404)
    row = await _create_version(
        session=session,
        background_tasks=background_tasks,
        current_user_id=current_user.id,
        document=document,
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        upload=file,
    )
    return success({"version_id": row.id}, message="新版本已上传，正在建立索引")


@router.post("/versions/{version_id}/publish")
async def publish_version(
    version_id: int, current_user: AdminUser, session: AsyncSession = Depends(get_db)
) -> dict:
    row = await session.get(KnowledgeDocumentVersion, version_id, with_for_update=True)
    if row is None:
        raise BusinessError(60104, "KNOWLEDGE_VERSION_NOT_FOUND", "政策版本不存在", 404)
    if row.status != KnowledgeVersionStatus.READY:
        raise BusinessError(60104, "KNOWLEDGE_NOT_READY", "只有索引完成的版本可以发布", 409)
    current_rows = (
        await session.scalars(
            select(KnowledgeDocumentVersion).where(
                KnowledgeDocumentVersion.document_id == row.document_id,
                KnowledgeDocumentVersion.status == KnowledgeVersionStatus.PUBLISHED,
            )
        )
    ).all()
    for current in current_rows:
        current.status = KnowledgeVersionStatus.ARCHIVED
    row.status = KnowledgeVersionStatus.PUBLISHED
    row.published_by = current_user.id
    row.published_at = datetime.now(timezone.utc)
    await record_audit(
        session,
        actor_user_id=current_user.id,
        action="KNOWLEDGE_VERSION_PUBLISH",
        resource_type="knowledge_document_version",
        resource_id=str(row.id),
        after={"document_id": row.document_id, "version": row.version},
    )
    await session.commit()
    return success(message="政策版本发布成功")


@router.post("/versions/{version_id}/archive")
async def archive_version(
    version_id: int, current_user: AdminUser, session: AsyncSession = Depends(get_db)
) -> dict:
    row = await session.get(KnowledgeDocumentVersion, version_id, with_for_update=True)
    if row is None:
        raise BusinessError(60104, "KNOWLEDGE_VERSION_NOT_FOUND", "政策版本不存在", 404)
    if row.status not in {KnowledgeVersionStatus.READY, KnowledgeVersionStatus.PUBLISHED}:
        raise BusinessError(60104, "KNOWLEDGE_VERSION_STATE_INVALID", "当前状态不能归档", 409)
    row.status = KnowledgeVersionStatus.ARCHIVED
    await record_audit(
        session,
        actor_user_id=current_user.id,
        action="KNOWLEDGE_VERSION_ARCHIVE",
        resource_type="knowledge_document_version",
        resource_id=str(row.id),
    )
    await session.commit()
    return success(message="政策版本已归档")


@router.post("/versions/{version_id}/retry")
async def retry_version(
    version_id: int,
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    row = await session.get(KnowledgeDocumentVersion, version_id, with_for_update=True)
    if row is None:
        raise BusinessError(60104, "KNOWLEDGE_VERSION_NOT_FOUND", "政策版本不存在", 404)
    if row.status != KnowledgeVersionStatus.FAILED:
        raise BusinessError(60104, "KNOWLEDGE_VERSION_STATE_INVALID", "只有失败任务可以重试", 409)
    latest_attempt = await session.scalar(
        select(func.max(KnowledgeIndexJob.attempt)).where(
            KnowledgeIndexJob.version_id == version_id
        )
    )
    row.status = KnowledgeVersionStatus.UPLOADED
    row.failure_reason = None
    job = KnowledgeIndexJob(
        version_id=version_id,
        status=KnowledgeJobStatus.PENDING,
        attempt=(latest_attempt or 0) + 1,
    )
    session.add(job)
    await session.flush()
    await record_audit(
        session,
        actor_user_id=current_user.id,
        action="KNOWLEDGE_INDEX_RETRY",
        resource_type="knowledge_document_version",
        resource_id=str(row.id),
        after={"attempt": job.attempt},
    )
    await session.commit()
    background_tasks.add_task(process_knowledge_version, row.id, job.id)
    return success(message="已重新提交索引任务")
