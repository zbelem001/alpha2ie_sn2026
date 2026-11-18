"""Registre des accords : enregistrer une décision du citoyen, la retirer, la consulter.

Chaque décision et chaque retrait sont inscrits dans la couche journal avant d'être validés :
si le journal ne les inscrit pas, rien n'est enregistré (JournalUnavailable, 503).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from .models import Base, ConsentRecord
from .schemas import Consent, ConsentIn, as_utc


class ConsentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_active(record: ConsentRecord, now: datetime) -> bool:
    return record.status == "granted" and record.expires_at is not None and as_utc(record.expires_at) > now


def consent_purpose(record: ConsentRecord) -> str:
    if record.status == "refused":
        return "accord refusé par le citoyen"
    if record.channel == "web":
        return "accord donné par le citoyen sur l'espace usager"
    if record.channel == "assisted":
        if (record.evidence_ref or "").startswith("consent-otp-simulated:"):
            return "accord confirmé au guichet par code simulé ; aucun téléphone vérifié"
        return "accord confirmé au guichet par code à usage unique reçu par SMS"
    return "accord recueilli au guichet"


class ConsentStore:
    def __init__(self, engine: Engine, journal: Any, clock: Callable[[], datetime] = utc_now) -> None:
        self._engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False)
        self._journal = journal
        self._clock = clock
        self._lock = threading.Lock()

    def create_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def now(self) -> datetime:
        return as_utc(self._clock())

    def view(self, record: ConsentRecord) -> Consent:
        return Consent(
            id=record.id, case_id=record.case_id, subject_ref=record.subject_ref,
            requester_code=record.requester_code, requester_name=record.requester_name,
            procedure_code=record.procedure_code, status=record.status, active=is_active(record, self.now()),
            channel=record.channel, notice_version=record.notice_version, evidence_ref=record.evidence_ref,
            scope=record.scope, created_at=record.created_at, granted_at=record.granted_at,
            expires_at=record.expires_at, revoked_at=record.revoked_at,
        )

    def _trace(self, record: ConsentRecord, event_type: str, outcome: str, purpose: str) -> None:
        self._journal.append({
            "event_type": event_type, "subject_ref": record.subject_ref, "case_id": record.case_id,
            "procedure_code": record.procedure_code, "actor_type": "citizen", "actor_ref": record.subject_ref,
            "requester_code": record.requester_code, "requester_name": record.requester_name,
            "purpose": purpose, "outcome": outcome,
            "data_categories": [item["question_code"] for item in record.scope], "consent_id": str(record.id),
        })

    def record(self, body: ConsentIn) -> Consent:
        now = self.now()
        if body.decision == "granted" and as_utc(body.expires_at) <= now:
            raise ConsentError(422, "L'accord doit expirer dans le futur")
        with self._lock, self._sessions.begin() as session:
            # Une nouvelle décision remplace l'accord en cours du dossier.
            for previous in session.scalars(select(ConsentRecord).where(
                ConsentRecord.case_id == body.case_id, ConsentRecord.status == "granted",
            )):
                previous.status, previous.revoked_at = "revoked", now
            record = ConsentRecord(
                id=uuid4(), case_id=body.case_id, subject_ref=body.subject_ref, requester_code=body.requester_code,
                requester_name=body.requester_name, procedure_code=body.procedure_code, status=body.decision,
                channel=body.channel, notice_version=body.notice_version, evidence_ref=body.evidence_ref,
                scope=[item.model_dump() for item in body.scope], created_at=now,
                granted_at=now if body.decision == "granted" else None,
                expires_at=as_utc(body.expires_at) if body.expires_at else None,
            )
            session.add(record)
            session.flush()
            self._trace(record, "consent_recorded", body.decision, consent_purpose(record))
        return self.view(record)

    def revoke(self, consent_id: UUID) -> Consent:
        now = self.now()
        with self._lock, self._sessions.begin() as session:
            record = session.get(ConsentRecord, consent_id)
            if record is None:
                raise ConsentError(404, "Accord introuvable")
            if not is_active(record, now):
                raise ConsentError(409, "Aucun accord actif à retirer")
            record.status, record.revoked_at = "revoked", now
            self._trace(record, "consent_revoked", "revoked", "retrait de l'accord par le citoyen")
        return self.view(record)

    def get_record(self, consent_id: UUID) -> ConsentRecord | None:
        with self._sessions() as session:
            return session.get(ConsentRecord, consent_id)

    def get(self, consent_id: UUID) -> Consent | None:
        record = self.get_record(consent_id)
        return self.view(record) if record is not None else None

    def search(self, *, case_id: str | None = None, subject_ref: str | None = None,
               active: bool | None = None) -> list[Consent]:
        query = select(ConsentRecord).order_by(ConsentRecord.created_at.desc())
        if case_id is not None:
            query = query.where(ConsentRecord.case_id == case_id)
        if subject_ref is not None:
            query = query.where(ConsentRecord.subject_ref == subject_ref)
        with self._sessions() as session:
            consents = [self.view(record) for record in session.scalars(query.limit(500))]
        return [consent for consent in consents if active is None or consent.active == active]
