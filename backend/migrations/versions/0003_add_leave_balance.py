"""create annual leave balance table"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_leave_balance"
down_revision = "0002_soft_delete_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "leave_balance" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "leave_balance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_type.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quota", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance_employee_type_year"),
    )
    op.create_index("ix_leave_balance_employee_id", "leave_balance", ["employee_id"])
    op.create_index("ix_leave_balance_leave_type_id", "leave_balance", ["leave_type_id"])
    op.create_index("ix_leave_balance_year", "leave_balance", ["year"])


def downgrade() -> None:
    if "leave_balance" in inspect(op.get_bind()).get_table_names():
        op.drop_table("leave_balance")
