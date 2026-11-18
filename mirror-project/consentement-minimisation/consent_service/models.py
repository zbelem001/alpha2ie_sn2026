"""Registre des accords : un accord par décision du citoyen, pour un dossier.

Un nouvel accord sur un dossier remplace le précédent (statut « revoked ») ; « expiré » se
déduit de expires_at. Le périmètre (scope) liste exactement ce que l'accord couvre :
pour chaque question, le détenteur et le service interrogés.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConsentRecord(Base):
    __tablename__ = "consents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    requester_code: Mapped[str] = mapped_column(String(160), nullable=False)
    requester_name: Mapped[str | None] = mapped_column(String(200))
    procedure_code: Mapped[str] = mapped_column(String(64), nullable=False)
    # granted | refused | revoked
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    notice_version: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(200))
    scope: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
