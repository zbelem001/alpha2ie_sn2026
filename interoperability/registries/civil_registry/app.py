"""Registre d'état civil simulé (Mairie de Ouagadougou).

Services :
- identity        : identité nécessaire à un titre (recherche par identifiant pivot ou par critères)
- identity-match  : « correspond : oui/non » entre un identifiant pivot et ce que déclare l'usager
- is-adult        : « majeur : oui/non », jamais la date de naissance
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
    age_on,
    create_registry_app,
    load_records,
    matches_criteria,
    reference_date,
    resolve_single,
)

ORGANIZATION = "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
DATA_FILE = Path(__file__).parent / "data" / "records.json"
ADULT_AGE = 18


def create_app(records: list[Record] | None = None, today: Callable[[], date] = reference_date) -> FastAPI:
    records = load_records(DATA_FILE) if records is None else records

    def identity(request: RegistryRequest) -> ServiceResult:
        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            return found
        return ServiceResult.ok(
            {
                "pivot_id": found["pivot_id"],
                "last_name": found["last_name"],
                "first_names": found["first_names"],
                "sex": found["sex"],
                "birth_date": found["birth_date"],
                "birth_place": found["birth_place"],
                "birth_country": found["birth_country"],
                "born_in_burkina": found["birth_country"] == "BF",
                "deceased": found.get("death_date") is not None,
            }
        )

    def identity_match(request: RegistryRequest) -> ServiceResult:
        subject = request.subject
        if not (subject.pivot_id and subject.has_criteria):
            return ServiceResult.invalid(
                "identity-match exige pivot_id, last_name, first_names et birth_date"
            )
        candidates = [record for record in records if record["pivot_id"] == subject.pivot_id]
        if not candidates:
            return ServiceResult.not_found()
        if len(candidates) > 1:
            return ServiceResult.ambiguous()
        # Réponse fermée : on ne dit pas quel champ diffère.
        return ServiceResult.ok({"match": matches_criteria(candidates[0], subject)})

    def is_adult(request: RegistryRequest) -> ServiceResult:
        found = resolve_single(records, request.subject)
        if isinstance(found, ServiceResult):
            return found
        age = age_on(date.fromisoformat(found["birth_date"]), today())
        return ServiceResult.ok({"adult": age >= ADULT_AGE})

    definition = RegistryDefinition(
        name="État civil — Mairie de Ouagadougou",
        organization=ORGANIZATION,
        description=__doc__ or "",
        services={
            "identity": identity,
            "identity-match": identity_match,
            "is-adult": is_adult,
        },
    )
    return create_registry_app(definition)


app = create_app()
