"""Add platform inbox and simulated SMS consent notifications."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_consent_notifications"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_ref", sa.String(length=160), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("channel IN ('platform','sms')", name="ck_notifications_channel"),
        sa.CheckConstraint(
            "delivery_status IN ('delivered','simulated','failed')",
            name="ck_notifications_delivery_status",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_notifications_case_id", "notifications", ["case_id"])
    op.create_index("ix_notifications_recipient_ref", "notifications", ["recipient_ref"])


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_ref", table_name="notifications")
    op.drop_index("ix_notifications_case_id", table_name="notifications")
    op.drop_table("notifications")
