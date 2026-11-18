"""Chaîne d'empreintes : l'empreinte de chaque événement couvre tous ses champs et celle du précédent.

Modifier, retirer ou intercaler un événement casse la chaîne à partir de cet endroit ;
GET /v1/chain/verify la recalcule de bout en bout.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

HASHED_FIELDS = (
    "id", "sequence", "occurred_at", "source", "event_type", "subject_ref", "case_id", "procedure_code",
    "actor_type", "actor_ref", "requester_code", "requester_name", "holder_code", "holder_name",
    "registry_code", "question_code", "service_code", "purpose", "outcome", "data_categories",
    "consent_id", "correlation_id", "previous_hash",
)


def as_utc(value: datetime) -> datetime:
    """SQLite rend les dates sans fuseau : elles sont enregistrées en UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _plain(value: Any) -> Any:
    if isinstance(value, datetime):
        return as_utc(value).isoformat(timespec="microseconds")
    if isinstance(value, UUID):
        return str(value)
    return value


def event_hash(event: Any) -> str:
    fields = {name: _plain(getattr(event, name)) for name in HASHED_FIELDS}
    canonical = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
