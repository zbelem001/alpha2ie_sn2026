"""Store encrypted citizen supplied registry identifiers."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_citizen_document_identifiers"
down_revision = "0004_citizen_identity_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("registry_requests", sa.Column("lookup_identifier_type", sa.String(length=80), nullable=True))
    op.add_column("registry_requests", sa.Column("lookup_identifier_ciphertext", sa.Text(), nullable=True))
    op.create_table(
        "citizen_document_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("principal_sub", sa.String(length=160), nullable=False),
        sa.Column("subject_ref", sa.String(length=160), nullable=False),
        sa.Column("identifier_type", sa.String(length=80), nullable=False),
        sa.Column("registry_code", sa.String(length=120), nullable=False),
        sa.Column("identifier_ciphertext", sa.Text(), nullable=False),
        sa.Column("identifier_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["principal_sub"], ["citizen_identity_links.principal_sub"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("principal_sub", "identifier_type", name="uq_citizen_identifier_account_type"),
        sa.UniqueConstraint("identifier_digest", name="uq_citizen_identifier_digest"),
    )
    op.create_index("ix_citizen_document_identifiers_principal_sub", "citizen_document_identifiers", ["principal_sub"])
    op.create_index("ix_citizen_document_identifiers_subject_ref", "citizen_document_identifiers", ["subject_ref"])


def downgrade() -> None:
    op.drop_index("ix_citizen_document_identifiers_subject_ref", table_name="citizen_document_identifiers")
    op.drop_index("ix_citizen_document_identifiers_principal_sub", table_name="citizen_document_identifiers")
    op.drop_table("citizen_document_identifiers")
    op.drop_column("registry_requests", "lookup_identifier_ciphertext")
    op.drop_column("registry_requests", "lookup_identifier_type")
