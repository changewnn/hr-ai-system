"""add policy knowledge base and pgvector storage"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0005_knowledge_base"
down_revision = "0004_salary_tax"
branch_labels = None
depends_on = None


knowledge_version_status = postgresql.ENUM(
    "UPLOADED",
    "PARSING",
    "INDEXING",
    "READY",
    "PUBLISHED",
    "ARCHIVED",
    "FAILED",
    name="knowledge_version_status_enum",
    create_type=False,
)
knowledge_job_status = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    name="knowledge_job_status_enum",
    create_type=False,
)


def upgrade() -> None:
    extension_available = (
        op.get_bind()
        .execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        .scalar()
    )
    if not extension_available:
        raise RuntimeError(
            "当前数据库未启用 pgvector。请使用数据库管理员在目标数据库执行 "
            "CREATE EXTENSION vector 后重新运行 Alembic 迁移。"
        )
    knowledge_version_status.create(op.get_bind(), checkfirst=True)
    knowledge_job_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_knowledge_document_name"),
    )
    op.create_index("ix_knowledge_document_name", "knowledge_document", ["name"])
    op.create_index("ix_knowledge_document_category", "knowledge_document", ["category"])
    op.create_index("ix_knowledge_document_created_by", "knowledge_document", ["created_by"])

    op.create_table(
        "knowledge_document_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_document.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("status", knowledge_version_status, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(150), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "published_by",
            sa.Integer(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "version", name="uq_knowledge_document_version"),
        sa.UniqueConstraint("document_id", "checksum", name="uq_knowledge_document_checksum"),
    )
    op.create_index(
        "ix_knowledge_version_document_id", "knowledge_document_version", ["document_id"]
    )
    op.create_index("ix_knowledge_version_status", "knowledge_document_version", ["status"])
    op.create_index("ix_knowledge_version_created_by", "knowledge_document_version", ["created_by"])
    op.create_index(
        "ix_knowledge_version_status_dates",
        "knowledge_document_version",
        ["status", "effective_from", "effective_to"],
    )

    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_document_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(300), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("version_id", "chunk_index", name="uq_knowledge_chunk_index"),
    )
    op.create_index("ix_knowledge_chunk_version_id", "knowledge_chunk", ["version_id"])
    op.create_index(
        "ix_knowledge_chunk_version_section", "knowledge_chunk", ["version_id", "section"]
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunk_embedding_hnsw ON knowledge_chunk "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "knowledge_index_job",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_document_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", knowledge_job_status, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_job_version_id", "knowledge_index_job", ["version_id"])
    op.create_index("ix_knowledge_job_status", "knowledge_index_job", ["status"])
    op.create_index(
        "ix_knowledge_job_status_created", "knowledge_index_job", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("knowledge_index_job")
    op.drop_table("knowledge_chunk")
    op.drop_table("knowledge_document_version")
    op.drop_table("knowledge_document")
    knowledge_job_status.drop(op.get_bind(), checkfirst=True)
    knowledge_version_status.drop(op.get_bind(), checkfirst=True)
