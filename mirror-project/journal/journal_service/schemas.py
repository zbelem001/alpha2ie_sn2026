"""Contrat de la couche journal (spécification générée : journal/openapi.yaml)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .chain import as_utc

ActorType = Literal["citizen", "agent", "administration", "system"]


class EventIn(BaseModel):
    """Événement à inscrire. Jamais de valeur issue d'un registre : des références, des codes, un résultat."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: str = Field(min_length=2, max_length=60, pattern=r"^[a-z][a-z0-9_]*$",
                            description="Type d'événement (ex. registry_check, consent_recorded, holder_refusal)")
    subject_ref: str = Field(min_length=1, max_length=160,
                             description="Citoyen concerné (ex. ACTE:OUAGA:2004:01234)")
    case_id: str | None = Field(default=None, max_length=64, description="Demande (dossier) concernée")
    procedure_code: str | None = Field(default=None, max_length=64, description="Démarche")
    actor_type: ActorType = Field(default="system", description="Qui agit")
    actor_ref: str | None = Field(default=None, max_length=160)
    requester_code: str | None = Field(default=None, max_length=160,
                                       description="Administration demandeuse (identifiant X-Road)")
    requester_name: str | None = Field(default=None, max_length=200)
    holder_code: str | None = Field(default=None, max_length=160,
                                    description="Administration qui détient la donnée (identifiant X-Road)")
    holder_name: str | None = Field(default=None, max_length=200)
    registry_code: str | None = Field(default=None, max_length=80)
    question_code: str | None = Field(default=None, max_length=80, description="Question posée (ex. candidate_minimum_age)")
    service_code: str | None = Field(default=None, max_length=80, description="Service du registre (ex. is-adult)")
    purpose: str = Field(min_length=1, max_length=200, description="Finalité ou motif, en clair")
    outcome: str | None = Field(default=None, max_length=40,
                                description="Résultat : confirmed, rejected, refused, unavailable, blocked…")
    data_categories: list[str] | None = Field(default=None, max_length=20,
                                              description="Catégories de données concernées, jamais leurs valeurs")
    consent_id: str | None = Field(default=None, max_length=64, description="Accord sur lequel repose l'événement")
    correlation_id: str | None = Field(default=None, max_length=160,
                                       description="Relie les événements d'une même consultation (identifiant de requête)")


class Event(EventIn):
    """Événement inscrit, avec son numéro d'ordre et son empreinte."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int = Field(description="Ordre d'inscription, sans trou")
    occurred_at: datetime
    source: str = Field(description="Couche qui a inscrit l'événement, déduite de son jeton")
    previous_hash: str | None
    event_hash: str

    @field_validator("occurred_at")
    @classmethod
    def _in_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class EventPage(BaseModel):
    events: list[Event]
    next_after: int | None = Field(description="À repasser dans « after » pour la page suivante ; null : dernière page")


class ChainReport(BaseModel):
    valid: bool = Field(description="La chaîne d'empreintes est intacte")
    events: int = Field(description="Événements vérifiés")
    first_invalid_sequence: int | None = Field(description="Premier événement modifié, retiré ou intercalé")
    last_hash: str | None = Field(description="Empreinte du dernier événement (chaîne intacte)")
