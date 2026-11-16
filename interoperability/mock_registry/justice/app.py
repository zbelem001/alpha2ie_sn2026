"""Registres simulés de la Justice (nationalité et casier judiciaire).

Services :
- nationality     : « burkinabè : oui/non », sans le mode d'acquisition
- criminal-record : « casier vierge : oui/non », sans le détail des condamnations
Une personne inconnue de la Justice donne « not_found » : jamais « oui » par défaut.
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
    resolve_single,
)

ORGANIZATION = "BF/GOV/JUSTICE/REGISTRES"
DATA_FILE = Path(__file__).parent / "data" / "records.json"


def create_app(records: list[Record] | None = None) -> FastAPI:
    records = load_records(DATA_FILE) if records is None else records

    def nationality(request: RegistryRequest) -> ServiceResult:
        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            return found
        return ServiceResult.ok({"burkinabe": bool(found["burkinabe"])})

    def criminal_record(request: RegistryRequest) -> ServiceResult:
        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            return found
        return ServiceResult.ok({"clean": found["convictions"] == 0})

    definition = RegistryDefinition(
        name="Justice — nationalité et casier",
        organization=ORGANIZATION,
        description=__doc__ or "",
        services={"nationality": nationality, "criminal-record": criminal_record},
    )
    return create_registry_app(definition)


app = create_app()
