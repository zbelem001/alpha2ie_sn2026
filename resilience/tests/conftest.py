"""Toute la chaîne d'une vérification, en mémoire, avec des registres qu'on peut débrancher.

couche démarches (_run_checks, reprise) → connecteur direct de la passerelle
(routing.detenteurs.yaml) → garde de la couche consentement-minimisation → registres simulés ;
registre des accords et journal partagés, comme dans la pile Docker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import connectors
import httpx
import pytest
from connectors import HttpRegistryConnector, load_routes
from consent_client import ConsentClient
from consent_service.app import create_app as create_consent_app
from consent_service.holders import load_holders
from fastapi.testclient import TestClient
from journal_client import MemoryJournal
from mock_registry.justice.app import create_app as create_justice
from mock_registry.oni.app import create_app as create_oni
from mock_registry.treasury.app import create_app as create_treasury
from registries.civil_registry.app import create_app as create_civil
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.consents import use_consents
from app.database.base import Base
from app.journal import use_journal
from app.security import Principal
from scripts.seed_demo import seed

MIRROR = Path(__file__).resolve().parents[2]
ROUTES = MIRROR / "passerelle" / "connectors" / "routing.detenteurs.yaml"
TODAY = date(2026, 11, 18)
TOKEN = "jeton-resilience-demarches-0123"
AWA = "ACTE:OUAGA:2004:01234"
CITIZEN = Principal("citoyen-sub", frozenset({"citizen"}), None, AWA, display_name="Awa KABORE")
AGENT = Principal("agent-sub", frozenset({"agent"}), "BF/GOV/FONCTION-PUBLIQUE", None)
CONCOURS = "concours_direct_preverification"


class Registry(httpx.Client):
    """Registre simulé derrière une prise : arrêté (down), trop lent (slow) ou réponse forcée (reply)."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = TestClient(app)
        self.down = False
        self.slow = False
        self.reply: httpx.Response | None = None
        self.calls: list[str] = []

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append(kwargs["json"].get("request_id"))
        if self.down:
            raise httpx.ConnectError("registre arrêté")
        if self.slow:
            raise httpx.ReadTimeout("délai dépassé")
        if self.reply is not None:
            return self.reply
        kwargs.pop("timeout", None)
        return self.app.post(url, **kwargs)


@dataclass
class Stack:
    journal: MemoryJournal
    registries: dict[str, Registry]
    sessions: sessionmaker
    consents: ConsentClient
    guard_http: TestClient
    events: list = field(default_factory=list)

    def db(self) -> Session:
        return self.sessions()


@pytest.fixture
def stack(monkeypatch):
    journal = MemoryJournal(source="pile")
    registries = {
        "etat-civil": Registry(create_civil(today=lambda: TODAY)),
        "justice": Registry(create_justice()),
        "oni": Registry(create_oni()),
        "tresor": Registry(create_treasury()),
    }
    consent_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    consent_app = create_consent_app(engine=consent_engine, journal=journal, tokens={TOKEN: "demarches"},
                                     holders=load_holders(), registry_clients=registries, today=lambda: TODAY)
    guard_http = TestClient(consent_app)
    consents = ConsentClient("http://testserver", TOKEN, client=guard_http)

    def through_guard(request: httpx.Request) -> httpx.Response:
        reply = guard_http.request(request.method, request.url.path, content=request.content, headers=request.headers)
        return httpx.Response(reply.status_code, content=reply.content, headers=reply.headers)

    connector = HttpRegistryConnector(load_routes(ROUTES), client_id="BF/GOV/ONI/CNIB",
                                      client=httpx.Client(transport=httpx.MockTransport(through_guard)))
    monkeypatch.setattr(connectors, "build_connector", lambda: connector)
    use_journal(journal)
    use_consents(consents)

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        seed(db)
    yield Stack(journal=journal, registries=registries, sessions=sessions, consents=consents, guard_http=guard_http)
    use_journal(None)
    use_consents(None)
    engine.dispose()
    consent_engine.dispose()
