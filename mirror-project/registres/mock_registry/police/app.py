"""Registre simulé de la Police (déclarations de perte).

Services :
- loss-declaration : « perte déclarée : oui/non » pour un type de document
  (parameters.document_type, CNIB par défaut), avec la référence du procès-verbal si oui.
  Le registre ne contient que les déclarants : une personne absente n'a rien déclaré.
"""

from __future__ import annotations

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
    resolve_single,
)

ORGANIZATION = "BF/GOV/POLICE/PERTES"
DATA_FILE = Path(__file__).parent / "data" / "records.json"

NOT_DECLARED = {"declared": False, "reference": None, "declared_on": None}


def create_app(records: list[Record] | None = None) -> FastAPI:
    records = load_records(DATA_FILE) if records is None else records

    def loss_declaration(request: RegistryRequest) -> ServiceResult:
        document_type = request.parameters.get("document_type", "CNIB")
        if not isinstance(document_type, str) or not document_type:
            return ServiceResult.invalid("parameters.document_type doit être une chaîne non vide")

        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            if found.status is Status.NOT_FOUND:
                return ServiceResult.ok(dict(NOT_DECLARED))
            return found

        matching = [d for d in found["declarations"] if d["document_type"] == document_type.upper()]
        if not matching:
            return ServiceResult.ok(dict(NOT_DECLARED))
        latest = max(matching, key=lambda declaration: declaration["declared_on"])
        return ServiceResult.ok(
            {"declared": True, "reference": latest["reference"], "declared_on": latest["declared_on"]}
        )

    definition = RegistryDefinition(
        name="Police — déclarations de perte",
        organization=ORGANIZATION,
        description=__doc__ or "",
        services={"loss-declaration": loss_declaration},
    )
    return create_registry_app(definition)


app = create_app()
