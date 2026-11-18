"""openapi.yaml et schemas/consent.json restent ceux de l'application (régénérer : python -m consent_service.openapi)."""

from __future__ import annotations

import json

import yaml

from consent_service.openapi import CONSENT_SCHEMA_FILE, SPEC_FILE, consent_schema, specification


def test_published_specification_matches_the_application():
    assert yaml.safe_load(SPEC_FILE.read_text(encoding="utf-8")) == specification()


def test_published_consent_schema_matches_the_model():
    assert json.loads(CONSENT_SCHEMA_FILE.read_text(encoding="utf-8")) == consent_schema()


def test_the_guard_keeps_the_registry_contract_and_takes_consent_in_a_header():
    operation = specification()["paths"]["/holders/{holder}/services/{service}"]["post"]
    headers = {parameter["name"].lower() for parameter in operation["parameters"] if parameter["in"] == "header"}
    assert headers == {"x-road-client", "x-consent-id"}
