"""Construction et contrôle de l'enveloppe registry-response côté connecteur.

Ce module ne dépend pas du paquet `registries` : le backend peut installer les
connecteurs sans embarquer FastAPI ni les registres simulés.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    OK = "ok"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"


STATUSES = frozenset(status.value for status in Status)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def make_envelope(
    *,
    organization: str,
    service: str,
    status: Status,
    request_id: str | None,
    data: dict[str, Any] | None = None,
    message: str | None = None,
    responded_at: str | None = None,
    transport_id: str | None = None,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "organization": organization,
        "service": service,
        "status": status.value,
        "data": data if status is Status.OK else None,
        "message": message,
        "responded_at": responded_at or utc_now_iso(),
        "transport_id": transport_id,
    }


def is_well_formed(body: Any) -> bool:
    """Vrai si le corps reçu respecte l'essentiel du contrat (statut connu, données seulement si ok)."""
    if not isinstance(body, dict) or body.get("status") not in STATUSES:
        return False
    if body["status"] == Status.OK:
        return isinstance(body.get("data"), dict)
    return True
