"""Link citizen accounts, pivot references, and verified phone numbers."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_citizen_identity_links"
down_revision = "0003_twilio_sms_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citizen_identity_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("principal_sub", sa.String(length=160), nullable=False),
        sa.Column("subject_ref", sa.String(length=160), nullable=False),
        sa.Column("phone_number", sa.String(length=24), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("principal_sub", name="uq_citizen_identity_links_principal_sub"),
        sa.UniqueConstraint("subject_ref", name="uq_citizen_identity_links_subject_ref"),
    )


def downgrade() -> None:
    op.drop_table("citizen_identity_links")
