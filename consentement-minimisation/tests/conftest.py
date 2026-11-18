from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from journal_client import MemoryJournal
from mock_registry.justice.app import create_app as create_justice
from mock_registry.oni.app import create_app as create_oni
from mock_registry.police.app import create_app as create_police
from mock_registry.treasury.app import create_app as create_treasury
from registries.civil_registry.app import create_app as create_civil
from registries.transport_registry.app import create_app as create_transport
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from consent_service.app import create_app
from consent_service.holders import load_holders

LAYER = Path(__file__).resolve().parents[1]
REGISTRY_RESPONSE = Draft202012Validator(json.loads(
    (LAYER.parent / "registres" / "schemas" / "registry-response.json").read_text(encoding="utf-8")
))

TOKEN = "jeton-demarches-0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
TODAY = date(2026, 11, 18)
AWA = "ACTE:OUAGA:2004:01234"
FONCTION_PUBLIQUE = "BF/GOV/FONCTION-PUBLIQUE"
CIVIL = "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
JUSTICE = "BF/GOV/JUSTICE/REGISTRES"
TRESOR = "BF/GOV/TRESOR/PAIEMENTS"
CONCOURS = "concours_direct_preverification"
PASSEPORT = "passeport_ordinaire_precheck"


class Clock:
    """Horloge de test : avance d'une seconde à chaque lecture, pour des décisions ordonnées."""

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


def concours_consent(**overrides) -> dict:
    consent = {
        "case_id": "dossier-awa-1",
        "subject_ref": AWA,
        "requester_code": FONCTION_PUBLIQUE,
        "requester_name": "Fonction publique",
        "procedure_code": CONCOURS,
        "decision": "granted",
        "channel": "web",
        "notice_version": "espace-usager-v1",
        "expires_at": "2026-12-18T09:00:00Z",
        "scope": [
            {"question_code": "candidate_minimum_age", "holder_code": CIVIL, "service_code": "is-adult"},
            {"question_code": "candidate_nationality", "holder_code": JUSTICE, "service_code": "nationality"},
            {"question_code": "criminal_record_indicator", "holder_code": JUSTICE, "service_code": "criminal-record"},
        ],
    }
    consent.update(overrides)
    return consent


def registry_body(procedure: str = CONCOURS, pivot: str = AWA, request_id: str = "requete-1", **extra) -> dict:
    return {"request_id": request_id, "procedure": procedure, "subject": {"pivot_id": pivot}, "parameters": {}, **extra}


def registry_apps() -> dict[str, TestClient]:
    return {
        "etat-civil": TestClient(create_civil(today=lambda: TODAY)),
        "justice": TestClient(create_justice()),
        "oni": TestClient(create_oni()),
        "tresor": TestClient(create_treasury()),
        "transport": TestClient(create_transport(today=lambda: TODAY)),
        "police": TestClient(create_police()),
    }


@pytest.fixture
def journal():
    return MemoryJournal(source="consentement-minimisation")


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def registries():
    return registry_apps()


@pytest.fixture
def app(journal, clock, registries):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield create_app(engine=engine, journal=journal, tokens={TOKEN: "demarches"}, holders=load_holders(),
                     registry_clients=registries, clock=clock, today=lambda: TODAY)
    engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def granted(client) -> dict:
    response = client.post("/v1/consents", json=concours_consent(), headers=AUTH)
    assert response.status_code == 201, response.text
    return response.json()


def ask(client: TestClient, holder: str, service: str, body: dict, *, requester: str | None = FONCTION_PUBLIQUE,
        consent_id: str | None = None):
    headers = {}
    if requester:
        headers["X-Road-Client"] = requester
    if consent_id:
        headers["X-Consent-Id"] = consent_id
    response = client.post(f"/holders/{holder}/services/{service}", json=body, headers=headers)
    envelope = response.json()
    assert not list(REGISTRY_RESPONSE.iter_errors(envelope)), envelope
    return response.status_code, envelope


def later(days: int) -> str:
    return (datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc) + timedelta(days=days)).isoformat()
