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

    @model_validator(mode="after")
    def _must_identify_someone(self) -> Subject:
        if self.pivot_id is None and not self.has_criteria:
            raise ValueError("pivot_id, ou last_name + first_names + birth_date, est requis")
        return self


class RegistryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str | None = Field(default=None, max_length=128)
    procedure: str | None = Field(default=None, max_length=64)
    subject: Subject
    parameters: dict[str, Any] = Field(default_factory=dict)
