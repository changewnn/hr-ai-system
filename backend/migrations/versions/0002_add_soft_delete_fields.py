"""add soft delete fields to organization tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_soft_delete_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    for table in ("department", "position", "employee"):
        if "deleted_at" not in {column["name"] for column in inspector.get_columns(table)}:
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    for table in ("employee", "position", "department"):
        if "deleted_at" in {column["name"] for column in inspector.get_columns(table)}:
            op.drop_column(table, "deleted_at")
