"""extend agent conversation and policy consultation messages"""

import sqlalchemy as sa
from alembic import op

revision = "0006_agent_rag"
down_revision = "0005_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    conversation_columns = {item["name"] for item in inspector.get_columns("agent_conversation")}
    if "employee_id" not in conversation_columns:
        op.add_column("agent_conversation", sa.Column("employee_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_agent_conversation_employee",
            "agent_conversation",
            "employee",
            ["employee_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_agent_conversation_employee_id", "agent_conversation", ["employee_id"])
    if "status" not in conversation_columns:
        op.add_column(
            "agent_conversation",
            sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        )
        op.create_index("ix_agent_conversation_status", "agent_conversation", ["status"])
    if "checkpoint_id" not in conversation_columns:
        op.add_column(
            "agent_conversation", sa.Column("checkpoint_id", sa.String(128), nullable=True)
        )

    message_columns = {item["name"] for item in inspector.get_columns("agent_message")}
    if "citations" not in message_columns:
        op.add_column("agent_message", sa.Column("citations", sa.JSON(), nullable=True))
    if "status" not in message_columns:
        op.add_column(
            "agent_message",
            sa.Column("status", sa.String(20), nullable=False, server_default="COMPLETED"),
        )
    if "request_id" not in message_columns:
        op.add_column("agent_message", sa.Column("request_id", sa.String(64), nullable=True))
        op.create_index("ix_agent_message_request_id", "agent_message", ["request_id"])

    enum_exists = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_type_enum')")
    ).scalar()
    if enum_exists:
        bind.execute(
            sa.text("ALTER TYPE message_type_enum ADD VALUE IF NOT EXISTS 'POLICY_CONSULT'")
        )


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in a transactional migration.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    message_columns = {item["name"] for item in inspector.get_columns("agent_message")}
    if "request_id" in message_columns:
        op.drop_index("ix_agent_message_request_id", table_name="agent_message")
        op.drop_column("agent_message", "request_id")
    if "status" in message_columns:
        op.drop_column("agent_message", "status")
    if "citations" in message_columns:
        op.drop_column("agent_message", "citations")
    conversation_columns = {item["name"] for item in inspector.get_columns("agent_conversation")}
    if "checkpoint_id" in conversation_columns:
        op.drop_column("agent_conversation", "checkpoint_id")
    if "status" in conversation_columns:
        op.drop_index("ix_agent_conversation_status", table_name="agent_conversation")
        op.drop_column("agent_conversation", "status")
    if "employee_id" in conversation_columns:
        op.drop_index("ix_agent_conversation_employee_id", table_name="agent_conversation")
        op.drop_constraint(
            "fk_agent_conversation_employee", "agent_conversation", type_="foreignkey"
        )
        op.drop_column("agent_conversation", "employee_id")
