"""Support local OTP challenges without an external messaging provider."""

from alembic import op
import sqlalchemy as sa


revision = "0008_simulated_otp_codes"
down_revision = "0007_local_administration_console"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_consent_otp_delivery_status", "consent_otp_challenges", type_="check")
    op.create_check_constraint(
        "ck_consent_otp_delivery_status",
        "consent_otp_challenges",
        "delivery_status IN ('sent','simulated','failed','consumed','expired')",
    )
    op.alter_column("consent_otp_challenges", "provider_pin_id", existing_type=sa.String(128), nullable=True)
    op.add_column("consent_otp_challenges", sa.Column("code_digest", sa.String(64), nullable=True))
    op.alter_column("registration_otp_challenges", "provider_pin_id", existing_type=sa.String(128), nullable=True)
    op.add_column("registration_otp_challenges", sa.Column("code_digest", sa.String(64), nullable=True))


def downgrade() -> None:
    op.execute("DELETE FROM consent_otp_challenges WHERE provider_pin_id IS NULL")
    op.execute("DELETE FROM registration_otp_challenges WHERE provider_pin_id IS NULL")
    op.drop_column("registration_otp_challenges", "code_digest")
    op.alter_column("registration_otp_challenges", "provider_pin_id", existing_type=sa.String(128), nullable=False)
    op.drop_column("consent_otp_challenges", "code_digest")
    op.alter_column("consent_otp_challenges", "provider_pin_id", existing_type=sa.String(128), nullable=False)
    op.drop_constraint("ck_consent_otp_delivery_status", "consent_otp_challenges", type_="check")
    op.create_check_constraint(
        "ck_consent_otp_delivery_status",
        "consent_otp_challenges",
        "delivery_status IN ('sent','failed','consumed','expired')",
    )
