"""Persist one-time challenges for assisted citizen consent."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_consent_otp_challenges"
down_revision = "0005_citizen_document_identifiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("consent_channel", sa.String(length=16), server_default="web", nullable=False),
    )
    op.create_check_constraint("ck_cases_consent_channel", "cases", "consent_channel IN ('assisted','web')")
    op.create_table(
        "consent_otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_sub", sa.String(length=160), nullable=False),
        sa.Column("provider_pin_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("scope_digest", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempt_count BETWEEN 0 AND 5", name="ck_consent_otp_attempts"),
        sa.CheckConstraint(
            "delivery_status IN ('sent','failed','consumed','expired')",
            name="ck_consent_otp_delivery_status",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_consent_otp_challenges_case_id", "consent_otp_challenges", ["case_id"])
    op.create_table(
        "registration_otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=False),
        sa.Column("provider_pin_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempt_count BETWEEN 0 AND 5", name="ck_registration_otp_attempts"),
    )
    op.create_index("ix_registration_otp_challenges_phone_number", "registration_otp_challenges", ["phone_number"])


def downgrade() -> None:
    op.drop_index("ix_registration_otp_challenges_phone_number", table_name="registration_otp_challenges")
    op.drop_table("registration_otp_challenges")
    op.drop_index("ix_consent_otp_challenges_case_id", table_name="consent_otp_challenges")
    op.drop_table("consent_otp_challenges")
    op.drop_constraint("ck_cases_consent_channel", "cases", type_="check")
    op.drop_column("cases", "consent_channel")
