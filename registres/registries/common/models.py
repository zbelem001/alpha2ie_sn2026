"""Validation des requêtes (contrat : contracts/schemas/registry-request.json)."""

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
        if self.subject.pivot_id is None and not self.subject.has_criteria:
            if not (self.parameters.get("identifier_type") and self.parameters.get("document_identifier")):
                raise ValueError("subject ou parameters.identifier_type + document_identifier est requis")
        return self
