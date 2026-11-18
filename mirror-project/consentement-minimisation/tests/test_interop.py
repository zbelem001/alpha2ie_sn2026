"""De bout en bout, comme dans la pile : connecteur de la passerelle → garde → registre simulé.

Le connecteur suit passerelle/connectors/routing.detenteurs.yaml : chaque détenteur est joint
par la garde, avec le demandeur (X-Road-Client) et l'accord (X-Consent-Id) en en-têtes.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from connectors import HttpRegistryConnector, load_routes
from fastapi.testclient import TestClient

from .conftest import AUTH, CIVIL, CONCOURS, FONCTION_PUBLIQUE, JUSTICE, concours_consent

ROUTES = Path(__file__).resolve().parents[2] / "passerelle" / "connectors" / "routing.detenteurs.yaml"


def connector_through(app) -> HttpRegistryConnector:
    guard = TestClient(app)

    def route(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "consentement-minimisation"
        reply = guard.request(request.method, request.url.path, content=request.content, headers=request.headers)
        return httpx.Response(reply.status_code, content=reply.content, headers=reply.headers)

    return HttpRegistryConnector(load_routes(ROUTES), client_id="BF/GOV/ONI/CNIB",
                                 client=httpx.Client(transport=httpx.MockTransport(route)))


def test_every_holder_of_the_stack_is_reached_through_the_guard(app):
    routes = load_routes(ROUTES)
    holders = {holder.organization for holder in app.state.guard.holders.values()}
    assert set(routes) == holders
    assert all("/holders/" in url for url in routes.values())


def test_concours_checks_from_the_requester_side(app, client, journal):
    consent = client.post("/v1/consents", json=concours_consent(), headers=AUTH).json()
    connector = connector_through(app)
    payload = {"request_id": "r-age", "procedure": CONCOURS, "subject": {"pivot_id": "ACTE:OUAGA:2004:01234"}}

    adult = connector.query(CIVIL, "is-adult", payload, client_id=FONCTION_PUBLIQUE, consent_id=consent["id"])
    clean = connector.query(JUSTICE, "criminal-record", {**payload, "request_id": "r-casier"},
                            client_id=FONCTION_PUBLIQUE, consent_id=consent["id"])
    assert (adult["status"], adult["data"]) == ("ok", {"adult": True})
    assert (clean["status"], clean["data"]) == ("ok", {"clean": True})

    # Sans l'accord, la même demande est refusée par la garde.
    refused = connector.query(CIVIL, "is-adult", payload, client_id=FONCTION_PUBLIQUE)
    assert refused["status"] == "refused" and refused["data"] is None
    outcomes = [(event["correlation_id"], event["outcome"]) for event in journal.search(event_type=["holder_response", "holder_refusal"])]
    assert outcomes == [("r-age", "ok"), ("r-casier", "ok"), ("r-age", "refused")]
