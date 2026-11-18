"""Journal en mémoire, même interface que JournalClient, pour les tests des couches qui écrivent au journal.

Mêmes règles que le service (tests/test_client.py le vérifie) : champs autorisés et obligatoires,
ordre d'inscription, filtres de recherche. `unavailable = True` simule une panne du journal.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .client import JournalUnavailable

FIELDS = (
    "event_type", "subject_ref", "case_id", "procedure_code", "actor_type", "actor_ref", "requester_code",
    "requester_name", "holder_code", "holder_name", "registry_code", "question_code", "service_code", "purpose",
    "outcome", "data_categories", "consent_id", "correlation_id",
)
REQUIRED = ("event_type", "subject_ref", "purpose")
EXACT_FILTERS = ("subject_ref", "case_id", "correlation_id", "requester_code", "actor_type")
TEXT_FIELDS = ("event_type", "purpose", "actor_ref", "outcome")
FILTERS = {*EXACT_FILTERS, "event_type", "q", "occurred_from", "occurred_to", "order"}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class MemoryJournal:
    def __init__(self, source: str = "test") -> None:
        self.source = source
        self.events: list[dict[str, Any]] = []
        self.unavailable = False

    def _available(self) -> None:
        if self.unavailable:
            raise JournalUnavailable("Journal injoignable (panne simulée)")

    def append(self, event: Mapping[str, Any]) -> dict[str, Any]:
        self._available()
        unknown = sorted(set(event) - set(FIELDS))
        missing = [name for name in REQUIRED if not event.get(name)]
        if unknown or missing:
            raise JournalUnavailable(f"Événement non inscrit : champs inconnus {unknown}, manquants {missing}")
        stored: dict[str, Any] = {name: event.get(name) for name in FIELDS}
        stored["actor_type"] = stored["actor_type"] or "system"
        stored.update(
            id=str(uuid.uuid4()),
            sequence=len(self.events) + 1,
            occurred_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            source=self.source,
        )
        self.events.append(stored)
        return dict(stored)

    def get(self, event_id: str) -> dict[str, Any] | None:
        self._available()
        return next((dict(event) for event in self.events if event["id"] == str(event_id)), None)

    def search(self, *, limit: int | None = None, **filters: Any) -> list[dict[str, Any]]:
        self._available()
        unknown = set(filters) - FILTERS
        if unknown:
            raise TypeError(f"Filtres inconnus : {sorted(unknown)}")
        types = filters.get("event_type")
        types = [types] if isinstance(types, str) else types
        needle = (filters.get("q") or "").strip().lower()

        def keep(event: dict[str, Any]) -> bool:
            if any(filters.get(key) is not None and event[key] != filters[key] for key in EXACT_FILTERS):
                return False
            if types is not None and event["event_type"] not in types:
                return False
            if needle and not any(needle in (event[field] or "").lower() for field in TEXT_FIELDS):
                return False
            occurred = datetime.fromisoformat(event["occurred_at"])
            if filters.get("occurred_from") is not None and occurred < _utc(filters["occurred_from"]):
                return False
            if filters.get("occurred_to") is not None and occurred >= _utc(filters["occurred_to"]):
                return False
            return True

        found = [dict(event) for event in self.events if keep(event)]
        if filters.get("order") == "desc":
            found.reverse()
        return found if limit is None else found[:limit]
