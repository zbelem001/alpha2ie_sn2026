"""Store the optional citizen display name used by agent case screens."""

from alembic import op
import sqlalchemy as sa


revision = "0009_case_applicant_display_name"
down_revision = "0008_simulated_otp_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("applicant_name", sa.String(100), nullable=False, server_default="Citoyen"),
    )


def downgrade() -> None:
    op.drop_column("cases", "applicant_name")
