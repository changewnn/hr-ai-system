"""add agent tool confirmation state"""

import sqlalchemy as sa
from alembic import op

revision = "0007_agent_tools"
down_revision = "0006_agent_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_action",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("agent_conversation.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_action_conversation_id", "agent_action", ["conversation_id"])
    op.create_index("ix_agent_action_user_id", "agent_action", ["user_id"])
    op.create_index("ix_agent_action_token_hash", "agent_action", ["token_hash"], unique=True)
    op.create_index("ix_agent_action_status", "agent_action", ["status"])


def downgrade() -> None:
    op.drop_table("agent_action")
