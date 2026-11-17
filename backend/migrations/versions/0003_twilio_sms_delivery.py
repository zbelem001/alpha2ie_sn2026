"""Track Twilio delivery state for SMS notifications."""
from alembic import op
import sqlalchemy as sa


revision = "0003_twilio_sms_delivery"
down_revision = "0002_consent_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_notifications_delivery_status",
        "notifications",
        type_="check",
    )
    op.create_check_constraint(
        "ck_notifications_delivery_status",
        "notifications",
        "delivery_status IN ('queued','sent','delivered','simulated','failed')",
    )
    op.add_column("notifications", sa.Column("provider_message_id", sa.String(length=80), nullable=True))
    op.add_column("notifications", sa.Column("delivery_error", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "delivery_error")
    op.drop_column("notifications", "provider_message_id")
    op.drop_constraint(
        "ck_notifications_delivery_status",
        "notifications",
        type_="check",
    )
    op.create_check_constraint(
        "ck_notifications_delivery_status",
        "notifications",
        "delivery_status IN ('delivered','simulated','failed')",
    )
