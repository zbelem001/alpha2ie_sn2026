"""journal/openapi.yaml reste celui de l'application (régénérer : python -m journal_service.openapi > openapi.yaml)."""

from __future__ import annotations

from pathlib import Path

import yaml

from journal_service.openapi import specification

SPEC_FILE = Path(__file__).resolve().parents[1] / "openapi.yaml"


def test_published_specification_matches_the_application():
    assert yaml.safe_load(SPEC_FILE.read_text(encoding="utf-8")) == specification()


def test_specification_documents_search_by_citizen_request_and_date():
    parameters = {item["name"] for item in specification()["paths"]["/v1/events"]["get"]["parameters"]}
    assert {"subject_ref", "case_id", "correlation_id", "from", "to"} <= parameters


def test_no_route_changes_or_removes_an_event():
    methods = {method for path in specification()["paths"].values() for method in path}
    assert methods <= {"get", "post"}
