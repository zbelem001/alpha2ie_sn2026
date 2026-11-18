"""Validation des requêtes (contrat : registres/schemas/registry-request.json)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

PIVOT_PATTERN = r"^ACTE:[A-Z]+:[0-9]{4}:[0-9]{5}$"


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pivot_id: str | None = Field(default=None, pattern=PIVOT_PATTERN)
    last_name: str | None = Field(default=None, min_length=1)
    first_names: str | None = Field(default=None, min_length=1)
    birth_date: date | None = None
    birth_place: str | None = Field(default=None, min_length=1)
    # Nom de la mère tel qu'inscrit sur l'acte : élément connu du titulaire (identity-match).
    mother_name: str | None = Field(default=None, min_length=1, max_length=160)

    @property
    def has_criteria(self) -> bool:
        return bool(self.last_name and self.first_names and self.birth_date)

class RegistryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str | None = Field(default=None, max_length=128)
    procedure: str | None = Field(default=None, max_length=64)
    subject: Subject
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _must_provide_lookup(self) -> RegistryRequest:
        # Une référence de pièce désigne une fiche, elle ne dit pas à qui elle appartient :
        # l'identité attendue du titulaire est toujours requise.
        if self.subject.pivot_id is None and not self.subject.has_criteria:
            raise ValueError("subject.pivot_id ou les critères d'identité (nom, prénoms, date de naissance) sont requis")
        return self
