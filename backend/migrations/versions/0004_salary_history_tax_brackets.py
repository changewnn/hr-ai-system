"""add salary config history and tax brackets"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_salary_tax"
down_revision = "0003_leave_balance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    constraints = {item["name"] for item in inspector.get_unique_constraints("salary_config")}
    if "uq_salary_config_employee" in constraints:
        op.drop_constraint("uq_salary_config_employee", "salary_config", type_="unique")
    if "uq_salary_config_employee_effective" not in constraints:
        op.create_unique_constraint("uq_salary_config_employee_effective", "salary_config", ["employee_id", "effective_date"])
    if "tax_bracket" not in inspector.get_table_names():
        op.create_table(
            "tax_bracket",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lower_bound", sa.Numeric(12, 2), nullable=False),
            sa.Column("upper_bound", sa.Numeric(12, 2), nullable=True),
            sa.Column("tax_rate", sa.Numeric(6, 4), nullable=False),
            sa.Column("quick_deduction", sa.Numeric(12, 2), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, unique=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "tax_bracket" in inspector.get_table_names():
        op.drop_table("tax_bracket")
    constraints = {item["name"] for item in inspector.get_unique_constraints("salary_config")}
    if "uq_salary_config_employee_effective" in constraints:
        op.drop_constraint("uq_salary_config_employee_effective", "salary_config", type_="unique")
    if "uq_salary_config_employee" not in constraints:
        op.create_unique_constraint("uq_salary_config_employee", "salary_config", ["employee_id"])
