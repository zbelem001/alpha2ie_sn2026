"""Registre ONI simulé pour vérifier le statut d'une CNIB.

Le service ne renvoie que ``valid``. Il ne divulgue ni numéro de CNIB,
ni dates d'établissement/expiration, ni autres attributs d'identité.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from registries.common import (
    Record,
    RegistryDefinition,
    RegistryRequest,
    ServiceResult,
    create_registry_app,
    load_records,
    resolve_by_identifier,
    resolve_single,
)

ORGANIZATION = "BF/GOV/ONI/CNIB"
DATA_FILE = Path(__file__).parent / "data" / "records.json"


def create_app(records: list[Record] | None = None) -> FastAPI:
    records = load_records(DATA_FILE) if records is None else records

    def cnib_status(request: RegistryRequest) -> ServiceResult:
        if request.parameters.get("document_identifier"):
            found = resolve_by_identifier(records, request.parameters, "cnib_number", "cnib_number")
            if isinstance(found, ServiceResult):
                return found
            return ServiceResult.ok({"valid": bool(found["valid"])})
        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            return found
        return ServiceResult.ok({"valid": bool(found["valid"])})

    definition = RegistryDefinition(
        name="ONI — statut CNIB (simulé)",
        organization=ORGANIZATION,
        description=__doc__ or "",
        services={"cnib-status": cnib_status},
    )
    return create_registry_app(definition)


app = create_app()
