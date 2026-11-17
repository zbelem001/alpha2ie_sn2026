from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from mock_registry.justice.app import create_app as create_justice
from mock_registry.police.app import create_app as create_police
from mock_registry.treasury.app import create_app as create_treasury
from registries.civil_registry.app import create_app as create_civil
from registries.transport_registry.app import create_app as create_transport

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
TODAY = date(2026, 11, 16)


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((CONTRACTS / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


RESPONSE_SCHEMA = _validator("registry-response.json")
REQUEST_SCHEMA = _validator("registry-request.json")
NOTIFICATION_REQUEST_SCHEMA = _validator("notification-request.json")
NOTIFICATION_RESPONSE_SCHEMA = _validator("notification-response.json")
SMS_REPLY_SCHEMA = _validator("sms-reply.json")


def assert_conforms(validator: Draft202012Validator, document: Any) -> None:
    errors = [f"{list(error.path)}: {error.message}" for error in validator.iter_errors(document)]
    assert not errors, errors


def call(client: TestClient, service: str, subject: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """Appelle un service, vérifie que requête et réponse respectent le contrat, renvoie la réponse."""
    payload = {"request_id": "test-1", "subject": subject, **extra}
    assert_conforms(REQUEST_SCHEMA, payload)
    response = client.post(f"/services/{service}", json=payload)
    body = response.json()
    assert_conforms(RESPONSE_SCHEMA, body)
    return body


@pytest.fixture
def civil() -> TestClient:
    return TestClient(create_civil(today=lambda: TODAY))


@pytest.fixture
def transport() -> TestClient:
    return TestClient(create_transport(today=lambda: TODAY))


@pytest.fixture
def justice() -> TestClient:
    return TestClient(create_justice())


@pytest.fixture
def police() -> TestClient:
    return TestClient(create_police())


@pytest.fixture
def treasury() -> TestClient:
    return TestClient(create_treasury())
