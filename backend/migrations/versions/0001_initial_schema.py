"""Create the initial backend schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op

from app.database.base import Base
from app.database import models  # noqa: F401 - populate Base.metadata

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

INITIAL_TABLES = {
    "administrations",
    "registries",
    "questions",
    "permissions",
    "procedures",
    "procedure_questions",
    "cases",
    "consents",
    "consent_questions",
    "registry_requests",
    "request_attempts",
    "audit_events",
}


def upgrade() -> None:
    # Keep this baseline stable as models evolve; later tables belong in their
    # own revisions rather than being created ahead of their migration.
    tables = [table for table in Base.metadata.sorted_tables if table.name in INITIAL_TABLES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
