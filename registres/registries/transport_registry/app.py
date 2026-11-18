"""Registre des transports simulé (permis de conduire).

Services :
- driving-licence : « permis valide : oui/non », avec catégories et échéance seulement si valide.
  Le registre ne contient que les titulaires : une personne absente n'a pas de permis.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from fastapi import FastAPI

from registries.common import (
    Record,
    RegistryDefinition,
    RegistryRequest,
    ServiceResult,
    Status,
    create_registry_app,
    load_records,
    reference_date,
    resolve_single,
)

ORGANIZATION = "BF/GOV/TRANSPORT/PERMIS"
DATA_FILE = Path(__file__).parent / "data" / "records.json"

NO_VALID_LICENCE = {"valid": False, "categories": [], "expires_on": None}


def create_app(records: list[Record] | None = None, today: Callable[[], date] = reference_date) -> FastAPI:
    records = load_records(DATA_FILE) if records is None else records

    def driving_licence(request: RegistryRequest) -> ServiceResult:
        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            if found.status is Status.NOT_FOUND:
                return ServiceResult.ok(dict(NO_VALID_LICENCE))
            return found
        licence = found.get("driving_licence")
        if not licence or date.fromisoformat(licence["expires_on"]) < today():
            return ServiceResult.ok(dict(NO_VALID_LICENCE))
        return ServiceResult.ok(
            {"valid": True, "categories": licence["categories"], "expires_on": licence["expires_on"]}
        )

    definition = RegistryDefinition(
        name="Transports — permis de conduire",
        organization=ORGANIZATION,
        description=__doc__ or "",
        services={"driving-licence": driving_licence},
    )
    return create_registry_app(definition)


app = create_app()
