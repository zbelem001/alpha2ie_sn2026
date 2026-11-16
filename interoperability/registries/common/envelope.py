"""Enveloppe de réponse commune (contrat : contracts/schemas/registry-response.json)."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ServiceResult:
    """Résultat métier d'un service, avant mise sous enveloppe."""

    status: Status
    data: dict[str, Any] | None = None
    message: str | None = None

    @classmethod
    def ok(cls, data: dict[str, Any]) -> ServiceResult:
        return cls(Status.OK, data)

    @classmethod
    def not_found(cls, message: str = "Aucune fiche ne correspond") -> ServiceResult:
        return cls(Status.NOT_FOUND, message=message)

    @classmethod
    def ambiguous(cls) -> ServiceResult:
        return cls(Status.AMBIGUOUS, message="Plusieurs fiches correspondent ; aucune donnée transmise")

    @classmethod
    def invalid(cls, message: str) -> ServiceResult:
        return cls(Status.INVALID_REQUEST, message=message)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_envelope(
    *, organization: str, service: str, result: ServiceResult, request_id: str | None
) -> dict[str, Any]:
    # Seul « ok » transporte des données : un service qui en joindrait à un refus
    # ou à une ambiguïté serait neutralisé ici.
    data = result.data if result.status is Status.OK else None
    return {
        "request_id": request_id,
        "organization": organization,
        "service": service,
        "status": result.status.value,
        "data": data,
        "message": result.message,
        "responded_at": utc_now_iso(),
    }
