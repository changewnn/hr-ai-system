from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
from docx import Document
from pypdf import PdfReader
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.knowledge import (
    EMBEDDING_DIMENSION,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeIndexJob,
    KnowledgeJobStatus,
    KnowledgeVersionStatus,
)

ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
}


@dataclass(frozen=True)
class ParsedSegment:
    text: str
    section: str | None = None
    page_number: int | None = None


@dataclass(frozen=True)
class PreparedUpload:
    original_filename: str
    extension: str
    mime_type: str
    content: bytes
    checksum: str


def prepare_upload(
    filename: str | None, content_type: str | None, content: bytes
) -> PreparedUpload:
    settings = get_settings()
    safe_name = Path(filename or "").name
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_FILE_TYPES:
        raise ValueError("UNSUPPORTED_TYPE")
    if not content or len(content) > settings.knowledge_max_file_mb * 1024 * 1024:
        raise ValueError("FILE_SIZE")
    mime_type = (content_type or "application/octet-stream").lower().split(";", 1)[0]
    if mime_type not in ALLOWED_FILE_TYPES[extension]:
        raise ValueError("UNSUPPORTED_MIME")
    if extension == ".pdf" and not content.startswith(b"%PDF"):
        raise ValueError("INVALID_SIGNATURE")
    if extension == ".docx" and not content.startswith(b"PK"):
        raise ValueError("INVALID_SIGNATURE")
    return PreparedUpload(
        original_filename=safe_name[:255],
        extension=extension,
        mime_type=mime_type,
        content=content,
        checksum=hashlib.sha256(content).hexdigest(),
    )


def save_upload(upload: PreparedUpload) -> str:
    storage = Path(get_settings().knowledge_storage_path).expanduser().resolve()
    storage.mkdir(parents=True, exist_ok=True)
    target = storage / f"{uuid4().hex}{upload.extension}"
    target.write_bytes(upload.content)
    return str(target)


def _parse_pdf(content: bytes) -> list[ParsedSegment]:
    reader = PdfReader(BytesIO(content))
    segments = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append(
                ParsedSegment(text=text, section=f"第 {page_number} 页", page_number=page_number)
            )
    if sum(len(item.text) for item in segments) < 30:
        raise ValueError("OCR_NOT_SUPPORTED")
    return segments


def _parse_docx(content: bytes) -> list[ParsedSegment]:
    document = Document(BytesIO(content))
    segments: list[ParsedSegment] = []
    section: str | None = None
    buffer: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style and paragraph.style.name.lower().startswith("heading"):
            if buffer:
                segments.append(ParsedSegment(text="\n".join(buffer), section=section))
                buffer = []
            section = text
        else:
            buffer.append(text)
    if buffer:
        segments.append(ParsedSegment(text="\n".join(buffer), section=section))
    return segments


def _parse_text(content: bytes, markdown: bool) -> list[ParsedSegment]:
    text = content.decode("utf-8-sig").strip()
    if not text:
        return []
    if not markdown:
        return [ParsedSegment(text=text)]
    segments: list[ParsedSegment] = []
    section: str | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            if buffer:
                segments.append(ParsedSegment(text="\n".join(buffer).strip(), section=section))
                buffer = []
            section = re.sub(r"^#{1,6}\s+", "", line).strip()
        else:
            buffer.append(line)
    if buffer:
        segments.append(ParsedSegment(text="\n".join(buffer).strip(), section=section))
    return [item for item in segments if item.text]


def parse_document(path: str) -> list[ParsedSegment]:
    file_path = Path(path)
    content = file_path.read_bytes()
    extension = file_path.suffix.lower()
    if extension == ".pdf":
        segments = _parse_pdf(content)
    elif extension == ".docx":
        segments = _parse_docx(content)
    elif extension in {".md", ".txt"}:
        segments = _parse_text(content, markdown=extension == ".md")
    else:
        raise ValueError("UNSUPPORTED_TYPE")
    if not segments or not any(item.text.strip() for item in segments):
        raise ValueError("EMPTY_DOCUMENT")
    return segments


def chunk_segments(
    segments: list[ParsedSegment], chunk_size: int | None = None, overlap: int | None = None
) -> list[ParsedSegment]:
    settings = get_settings()
    size = chunk_size or settings.knowledge_chunk_size
    shared = settings.knowledge_chunk_overlap if overlap is None else overlap
    if shared >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
    chunks: list[ParsedSegment] = []
    for segment in segments:
        normalized = re.sub(r"[ \t]+", " ", segment.text).strip()
        start = 0
        while start < len(normalized):
            end = min(start + size, len(normalized))
            if end < len(normalized):
                split_at = max(
                    normalized.rfind("\n", start, end), normalized.rfind("。", start, end)
                )
                if split_at > start + size // 2:
                    end = split_at + 1
            text = normalized[start:end].strip()
            if text:
                chunks.append(
                    ParsedSegment(
                        text=text, section=segment.section, page_number=segment.page_number
                    )
                )
            if end >= len(normalized):
                break
            start = max(start + 1, end - shared)
    return chunks


async def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if not settings.embedding_base_url or not settings.embedding_api_key:
        raise RuntimeError(
            "千问向量模型配置缺失，请配置 HR_EMBEDDING_BASE_URL 和 HR_EMBEDDING_API_KEY"
        )
    if settings.embedding_dimension != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"向量维度配置为 {settings.embedding_dimension}，数据库要求 {EMBEDDING_DIMENSION}"
        )
    url = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
    results: list[list[float]] = []
    async with httpx.AsyncClient(timeout=settings.embedding_timeout_seconds) as client:
        for offset in range(0, len(texts), 16):
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
                json={
                    "model": settings.embedding_model,
                    "input": texts[offset : offset + 16],
                    "dimensions": settings.embedding_dimension,
                    "encoding_format": "float",
                },
            )
            if response.status_code >= 400:
                raise RuntimeError(f"千问向量服务调用失败（HTTP {response.status_code}）")
            payload = response.json()
            ordered = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
            batch = [item.get("embedding", []) for item in ordered]
            if len(batch) != len(texts[offset : offset + 16]) or any(
                len(vector) != EMBEDDING_DIMENSION for vector in batch
            ):
                raise RuntimeError("千问向量服务返回数量或维度不正确")
            results.extend(batch)
    return results


async def process_knowledge_version(version_id: int, job_id: int) -> None:
    async with AsyncSessionLocal() as session:
        try:
            version = await session.get(KnowledgeDocumentVersion, version_id)
            job = await session.get(KnowledgeIndexJob, job_id)
            if version is None or job is None or job.status != KnowledgeJobStatus.PENDING:
                return
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            job.status = KnowledgeJobStatus.RUNNING
            job.started_at = now
            version.status = KnowledgeVersionStatus.PARSING
            version.failure_reason = None
            await session.commit()

            segments = parse_document(version.storage_path)
            chunks = chunk_segments(segments)
            version.status = KnowledgeVersionStatus.INDEXING
            await session.commit()
            vectors = await embed_texts([item.text for item in chunks])

            await session.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.version_id == version_id)
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                session.add(
                    KnowledgeChunk(
                        version_id=version_id,
                        chunk_index=index,
                        content=chunk.text,
                        token_count=max(1, (len(chunk.text) + 3) // 4),
                        section=chunk.section,
                        page_number=chunk.page_number,
                        metadata_json={"source": version.original_filename},
                        embedding=vector,
                    )
                )
            version.status = KnowledgeVersionStatus.READY
            job.status = KnowledgeJobStatus.SUCCEEDED
            job.finished_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            version = await session.get(KnowledgeDocumentVersion, version_id)
            job = await session.get(KnowledgeIndexJob, job_id)
            message = _failure_message(exc)
            if version is not None:
                version.status = KnowledgeVersionStatus.FAILED
                version.failure_reason = message
            if job is not None:
                from datetime import datetime, timezone

                job.status = KnowledgeJobStatus.FAILED
                job.error_message = message
                job.finished_at = datetime.now(timezone.utc)
            await session.commit()


def _failure_message(exc: Exception) -> str:
    mapping = {
        "OCR_NOT_SUPPORTED": "扫描 PDF 暂不支持 OCR，请上传带文本层的 PDF",
        "EMPTY_DOCUMENT": "文档中没有可索引的文本",
        "UNSUPPORTED_TYPE": "不支持的文档类型",
    }
    return mapping.get(str(exc), str(exc)[:1000] or "文档索引失败")


async def search_chunks(query: str, version_id: int | None, limit: int) -> list[dict]:
    vector = (await embed_texts([query]))[0]
    async with AsyncSessionLocal() as session:
        distance = KnowledgeChunk.embedding.cosine_distance(vector)
        statement = (
            select(
                KnowledgeChunk,
                KnowledgeDocumentVersion,
                KnowledgeDocument,
                distance.label("distance"),
            )
            .join(
                KnowledgeDocumentVersion, KnowledgeDocumentVersion.id == KnowledgeChunk.version_id
            )
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .where(
                KnowledgeDocumentVersion.status.in_(
                    [KnowledgeVersionStatus.READY, KnowledgeVersionStatus.PUBLISHED]
                )
            )
            .order_by(distance)
            .limit(limit)
        )
        if version_id is not None:
            statement = statement.where(KnowledgeChunk.version_id == version_id)
        rows = (await session.execute(statement)).all()
        return [
            {
                "chunk_id": chunk.id,
                "version_id": chunk.version_id,
                "document_id": document.id,
                "document_name": document.name,
                "version": version.version,
                "section": chunk.section,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "score": round(max(0.0, 1.0 - float(distance_value)), 4),
            }
            for chunk, version, document, distance_value in rows
        ]
