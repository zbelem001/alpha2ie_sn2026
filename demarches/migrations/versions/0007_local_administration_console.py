"""Persist administration-console configuration and audit actions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_local_administration_console"
down_revision = "0006_consent_otp_challenges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("registries", sa.Column("name", sa.String(200), nullable=False, server_default="Registre"))
    op.add_column("registries", sa.Column("base_url", sa.String(500), nullable=True))
    op.add_column("registries", sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("registries", sa.Column("last_test_success", sa.Boolean(), nullable=True))

    op.add_column("permissions", sa.Column("status", sa.String(20), nullable=False, server_default="not_requested"))
    op.add_column("permissions", sa.Column("purpose", sa.Text(), nullable=True))
    op.add_column("permissions", sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE permissions SET status = CASE WHEN active THEN 'approved' ELSE 'not_requested' END")
    op.create_check_constraint(
        "ck_permissions_status",
        "permissions",
        "status IN ('approved','requested','suspended','not_requested')",
    )

    op.add_column("procedures", sa.Column("purpose", sa.Text(), nullable=False, server_default=""))
    op.add_column("procedures", sa.Column("consent_days", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("procedures", sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_check_constraint("ck_procedures_consent_days", "procedures", "consent_days BETWEEN 1 AND 30")

    op.add_column("procedure_questions", sa.Column("document_type", sa.String(40), nullable=True))
    op.add_column("procedure_questions", sa.Column("document_label", sa.String(160), nullable=True))
    op.add_column("procedure_questions", sa.Column("document_hint", sa.String(300), nullable=True))

    op.create_table(
        "administration_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("administration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_sub", sa.String(160), nullable=False),
        sa.Column("actor_name", sa.String(200), nullable=False),
        sa.Column("actor_role", sa.String(40), nullable=False, server_default="local-admin"),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("detail", sa.String(500), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["administration_id"], ["administrations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_administration_audit_events_administration_id", "administration_audit_events", ["administration_id"])
    op.create_index("ix_administration_audit_events_occurred_at", "administration_audit_events", ["occurred_at"])

    op.create_table(
        "registry_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["registry_id"], ["registries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registry_id", "code", name="uq_registry_services_registry_id"),
    )
    op.create_index("ix_registry_services_registry_id", "registry_services", ["registry_id"])


def downgrade() -> None:
    op.drop_index("ix_registry_services_registry_id", table_name="registry_services")
    op.drop_table("registry_services")
    op.drop_index("ix_administration_audit_events_occurred_at", table_name="administration_audit_events")
    op.drop_index("ix_administration_audit_events_administration_id", table_name="administration_audit_events")
    op.drop_table("administration_audit_events")
    op.drop_column("procedure_questions", "document_hint")
    op.drop_column("procedure_questions", "document_label")
    op.drop_column("procedure_questions", "document_type")
    op.drop_constraint("ck_procedures_consent_days", "procedures", type_="check")
    op.drop_column("procedures", "published")
    op.drop_column("procedures", "consent_days")
    op.drop_column("procedures", "purpose")
    op.drop_constraint("ck_permissions_status", "permissions", type_="check")
    op.drop_column("permissions", "requested_at")
    op.drop_column("permissions", "purpose")
    op.drop_column("permissions", "status")
    op.drop_column("registries", "last_test_success")
    op.drop_column("registries", "last_test_at")
    op.drop_column("registries", "base_url")
    op.drop_column("registries", "name")
