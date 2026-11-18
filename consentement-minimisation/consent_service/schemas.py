"""Contrat de la couche (spécification générée : openapi.yaml ; accord seul : schemas/consent.json)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Channel = Literal["web", "in_person", "assisted"]
SERVICE_CODE = r"^[a-z0-9]+(-[a-z0-9]+)*$"


def as_utc(value: datetime) -> datetime:
    """SQLite rend les dates sans fuseau : elles sont enregistrées en UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ScopeItem(BaseModel):
    """Une information couverte par l'accord : la question, et le service du détenteur qui y répond."""

    model_config = ConfigDict(extra="forbid")

    question_code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$",
                               examples=["candidate_minimum_age"])
    holder_code: str = Field(min_length=1, max_length=160, description="Détenteur (identifiant X-Road)",
                             examples=["BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"])
    service_code: str = Field(min_length=1, max_length=80, pattern=SERVICE_CODE, examples=["is-adult"])


class ConsentIn(BaseModel):
    """Décision du citoyen pour un dossier, transmise par la couche démarches."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=1, max_length=64, description="Dossier (demande)")
    subject_ref: str = Field(min_length=1, max_length=160, description="Citoyen (ex. ACTE:OUAGA:2004:01234)")
    requester_code: str = Field(min_length=1, max_length=160, description="Administration demandeuse (identifiant X-Road)")
    requester_name: str | None = Field(default=None, max_length=200)
    procedure_code: str = Field(min_length=1, max_length=64, description="Démarche")
    decision: Literal["granted", "refused"]
    channel: Channel = Field(description="web : espace usager ; assisted : code reçu par SMS au guichet ; in_person : au guichet")
    notice_version: str = Field(min_length=1, max_length=60, description="Version de l'information présentée au citoyen")
    expires_at: datetime | None = Field(default=None, description="Fin de validité, obligatoire pour un accord (avec fuseau)")
    evidence_ref: str | None = Field(default=None, max_length=200, description="Preuve du recueil (ex. défi du code)")
    scope: list[ScopeItem] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _coherent(self) -> ConsentIn:
        if self.decision == "granted" and self.expires_at is None:
            raise ValueError("expires_at est obligatoire pour un accord")
        if self.expires_at is not None and self.expires_at.utcoffset() is None:
            raise ValueError("expires_at doit inclure un fuseau horaire")
        codes = [item.question_code for item in self.scope]
        if len(codes) != len(set(codes)):
            raise ValueError("Une question ne figure qu'une fois dans l'accord")
        return self


class Consent(BaseModel):
    """Accord enregistré. active : accordé, ni retiré ni expiré."""

    id: UUID
    case_id: str
    subject_ref: str
    requester_code: str
    requester_name: str | None
    procedure_code: str
    status: Literal["granted", "refused", "revoked"]
    active: bool
    channel: Channel
    notice_version: str
    evidence_ref: str | None
    scope: list[ScopeItem]
    created_at: datetime
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None

    @field_validator("created_at", "granted_at", "expires_at", "revoked_at")
    @classmethod
    def _in_utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value is not None else None


class Subject(BaseModel):
    """Personne visée, comme dans le contrat des registres (registres/schemas/registry-request.json)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pivot_id: str | None = Field(default=None, max_length=160)
    last_name: str | None = Field(default=None, max_length=100)
    first_names: str | None = Field(default=None, max_length=160)
    birth_date: str | None = Field(default=None, max_length=10)
    birth_place: str | None = Field(default=None, max_length=160)
    mother_name: str | None = Field(default=None, max_length=160)


class RegistryRequest(BaseModel):
    """Corps reçu par la garde : celui du contrat des registres, transmis tel quel au registre."""

    model_config = ConfigDict(extra="forbid")

    request_id: str | None = Field(default=None, max_length=128)
    procedure: str | None = Field(default=None, max_length=64)
    subject: Subject
    parameters: dict[str, Any] = Field(default_factory=dict)

    def registry_payload(self) -> dict[str, Any]:
        return {"request_id": self.request_id, "procedure": self.procedure,
                "subject": self.subject.model_dump(exclude_none=True), "parameters": self.parameters}


class Envelope(BaseModel):
    """Réponse de la garde : l'enveloppe du contrat des registres (registry-response.json)."""

    request_id: str | None
    organization: str
    service: str
    status: Literal["ok", "not_found", "ambiguous", "refused", "unavailable", "invalid_request"]
    data: dict[str, Any] | None = Field(description="Réponse réduite à l'utile ; présente seulement si status = ok")
    message: str | None
    responded_at: str


class RuleView(BaseModel):
    service: str
    basis: Literal["consent", "citizen_request"]
    procedures: list[str]
    registry_service: str
    reduction: dict[str, Any] = Field(description="Règle de réduction : keep, found ou adult_from")
    transmits: str = Field(description="Ce qui sort de chez le détenteur, en clair")


class HolderView(BaseModel):
    slug: str
    organization: str
    name: str
    registry_url: str = Field(description="Registre interrogé par la garde")
    origin: str = Field(description="« base » (holders.yaml) ou fichier de branchement")
    services: list[RuleView]
