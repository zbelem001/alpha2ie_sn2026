from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from journal_service.app import create_app

DEMARCHES_TOKEN = "jeton-demarches-0123456789"
CONSENT_TOKEN = "jeton-consentement-0123456789"
AUDITOR_TOKEN = "jeton-auditeur-0123456789"
WRITE_TOKENS = {DEMARCHES_TOKEN: "demarches", CONSENT_TOKEN: "consentement-minimisation"}
READ_TOKENS = {DEMARCHES_TOKEN: "demarches", AUDITOR_TOKEN: "auditeur"}
DEMARCHES = {"Authorization": f"Bearer {DEMARCHES_TOKEN}"}
CONSENT = {"Authorization": f"Bearer {CONSENT_TOKEN}"}
AUDITOR = {"Authorization": f"Bearer {AUDITOR_TOKEN}"}

AWA = "ACTE:OUAGA:2004:01234"
OTHER = "ACTE:BOBO:1999:00042"


class FakeClock:
    """Horloge réglable : chaque lecture avance d'une minute, pour des dates distinctes et ordonnées."""

    def __init__(self, start: datetime = datetime(2026, 11, 18, 8, 0, tzinfo=timezone.utc)) -> None:
        self.now = start

    def __call__(self) -> datetime:
        current = self.now
        self.now += timedelta(minutes=1)
        return current


def consultation(**overrides):
    event = {
        "event_type": "registry_check",
        "subject_ref": AWA,
        "case_id": "c0ffee00-0000-4000-8000-000000000001",
        "procedure_code": "concours_direct_preverification",
        "actor_type": "administration",
        "requester_code": "BF/GOV/FONCTION-PUBLIQUE",
        "requester_name": "Fonction publique",
        "holder_code": "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
        "holder_name": "État civil",
        "question_code": "candidate_minimum_age",
        "service_code": "is-adult",
        "purpose": "Vérifier l'âge minimum du candidat",
        "outcome": "confirmed",
        "data_categories": ["candidate_minimum_age"],
        "correlation_id": "requete-1",
    }
    event.update(overrides)
    return event


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield engine
    engine.dispose()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def app(engine, clock):
    return create_app(engine=engine, write_tokens=WRITE_TOKENS, read_tokens=READ_TOKENS, clock=clock)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
