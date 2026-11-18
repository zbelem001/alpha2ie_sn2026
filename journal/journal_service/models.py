"""Table unique du journal : des événements ajoutés à la suite, jamais modifiés ni supprimés.

Un événement ne contient aucune valeur issue d'un registre (date de naissance, nom…) :
des références (citoyen, dossier, accord), des codes (démarche, question, administrations)
et le résultat. En PostgreSQL, un déclencheur refuse toute modification ou suppression
(journal_service/start.py) ; la chaîne d'empreintes rend visible toute altération (chain.py).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JournalEvent(Base):
    __tablename__ = "journal_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # Ordre d'inscription, sans trou : un événement retiré se voit.
    sequence: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # Couche qui a inscrit l'événement, déduite de son jeton (jamais fournie par l'appelant).
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    case_id: Mapped[str | None] = mapped_column(String(64), index=True)
    procedure_code: Mapped[str | None] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(160))
    requester_code: Mapped[str | None] = mapped_column(String(160), index=True)
    requester_name: Mapped[str | None] = mapped_column(String(200))
    holder_code: Mapped[str | None] = mapped_column(String(160))
    holder_name: Mapped[str | None] = mapped_column(String(200))
    registry_code: Mapped[str | None] = mapped_column(String(80))
    question_code: Mapped[str | None] = mapped_column(String(80))
    service_code: Mapped[str | None] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(40))
    data_categories: Mapped[list | None] = mapped_column(JSON)
    consent_id: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str | None] = mapped_column(String(160), index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
