"""Connecteurs : comportement en cas de panne, et passage de bout en bout par les registres simulés."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from connectors import HttpRegistryConnector, XRoadConnector, build_connector, load_routes
from connectors.direct import DEFAULT_ROUTES_FILE
from mock_registry.justice.app import create_app as create_justice
from mock_registry.police.app import create_app as create_police
from mock_registry.treasury.app import create_app as create_treasury
from registries.civil_registry.app import create_app as create_civil
from registries.transport_registry.app import create_app as create_transport

from .conftest import RESPONSE_SCHEMA, TODAY, assert_conforms

CIVIL = "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
JUSTICE = "BF/GOV/JUSTICE/REGISTRES"
CLIENT_ID = "BF/GOV/ONI/CNIB"
AWA = {"subject": {"pivot_id": "ACTE:OUAGA:2004:01234"}, "procedure": "cnib-application"}


def connector_with(handler, routes=None) -> HttpRegistryConnector:
    return HttpRegistryConnector(
        routes or {CIVIL: "http://civil-registry:8000", JUSTICE: "http://justice-registry:8000"},
        client_id=CLIENT_ID,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def xroad_with(handler) -> XRoadConnector:
    return XRoadConnector(
        "http://ss-oni:8080", client_id=CLIENT_ID, client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def checked(envelope: dict) -> dict:
    assert_conforms(RESPONSE_SCHEMA, envelope)
    return envelope


# Bout en bout : connecteur direct -> registres simulés (en mémoire) ----------------------


@pytest.fixture
def live_connector() -> HttpRegistryConnector:
    apps = {
        "civil-registry": TestClient(create_civil(today=lambda: TODAY)),
        "transport-registry": TestClient(create_transport(today=lambda: TODAY)),
        "justice-registry": TestClient(create_justice()),
        "police-registry": TestClient(create_police()),
        "treasury-registry": TestClient(create_treasury()),
    }

    def route(request: httpx.Request) -> httpx.Response:
        app = apps[request.url.host]
        reply = app.request(request.method, request.url.path, content=request.content, headers=request.headers)
        return httpx.Response(reply.status_code, content=reply.content, headers=reply.headers)

    return HttpRegistryConnector(
        load_routes(DEFAULT_ROUTES_FILE),
        client_id=CLIENT_ID,
        client=httpx.Client(transport=httpx.MockTransport(route)),
    )


def test_cnib_scenario_for_awa(live_connector):
    identity = checked(live_connector.query(CIVIL, "identity", AWA))
    assert identity["status"] == "ok"
    assert identity["data"]["born_in_burkina"] is True
    assert identity["transport_id"] is None
    paid = checked(live_connector.query("BF/GOV/TRESOR/PAIEMENTS", "payment-status", AWA))
    assert paid["data"]["paid"] is True


def test_every_routed_registry_answers(live_connector):
    calls = {
        CIVIL: "is-adult",
        "BF/GOV/TRANSPORT/PERMIS": "driving-licence",
        JUSTICE: "nationality",
        "BF/GOV/POLICE/PERTES": "loss-declaration",
        "BF/GOV/TRESOR/PAIEMENTS": "payment-status",
    }
    for organization, service in calls.items():
        envelope = checked(live_connector.query(organization, service, AWA))
        assert envelope["status"] == "ok", (organization, envelope)
        assert envelope["organization"] == organization


def test_request_id_is_generated_and_kept(live_connector):
    envelope = checked(live_connector.query(CIVIL, "identity", AWA))
    assert envelope["request_id"]
    assert "request_id" not in AWA  # le payload de l'appelant n'est pas modifié


def test_registry_receives_xroad_client_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(404)

    connector_with(handler).query(CIVIL, "identity", AWA)
    assert seen["x-road-client"] == CLIENT_ID


# Pannes : jamais d'exception, jamais de données ------------------------------------------


def test_timeout_is_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("trop long", request=request)

    envelope = checked(connector_with(handler).query(JUSTICE, "nationality", AWA))
    assert envelope["status"] == "unavailable"
    assert envelope["message"] == "Délai d'attente dépassé"


def test_connection_refused_is_unavailable():
    def handler(request):
        raise httpx.ConnectError("refusé", request=request)

    envelope = checked(connector_with(handler).query(JUSTICE, "nationality", AWA))
    assert envelope["status"] == "unavailable"


def test_server_error_is_unavailable():
    envelope = checked(connector_with(lambda r: httpx.Response(502, text="Bad Gateway")).query(CIVIL, "identity", AWA))
    assert envelope["status"] == "unavailable"


def test_unreadable_body_is_unavailable():
    envelope = checked(connector_with(lambda r: httpx.Response(200, text="<html>")).query(CIVIL, "identity", AWA))
    assert envelope["status"] == "unavailable"


def test_ok_without_data_is_never_trusted():
    body = {"status": "ok", "data": None}
    envelope = checked(connector_with(lambda r: httpx.Response(200, json=body)).query(CIVIL, "identity", AWA))
    assert envelope["status"] == "unavailable"


def test_ok_with_error_http_code_is_not_trusted():
    body = {"status": "ok", "data": {"adult": True}}
    envelope = checked(connector_with(lambda r: httpx.Response(500, json=body)).query(CIVIL, "is-adult", AWA))
    assert envelope["status"] == "unavailable"


def test_data_attached_to_a_refusal_is_dropped():
    body = {"status": "ambiguous", "data": {"candidates": ["x", "y"]}, "message": "deux fiches"}
    envelope = checked(connector_with(lambda r: httpx.Response(200, json=body)).query(CIVIL, "identity", AWA))
    assert envelope["status"] == "ambiguous"
    assert envelope["data"] is None


def test_unknown_organization_is_invalid_request():
    envelope = checked(connector_with(lambda r: httpx.Response(200)).query("BF/GOV/INCONNU/X", "identity", AWA))
    assert envelope["status"] == "invalid_request"


def test_service_code_cannot_inject_a_path():
    called = []
    connector = connector_with(lambda r: called.append(r) or httpx.Response(200))
    envelope = checked(connector.query(CIVIL, "../admin", AWA))
    assert envelope["status"] == "invalid_request"
    assert not called


# Connecteur X-Road (réponses simulées) ------------------------------------------------


def test_xroad_url_and_headers():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["client"] = request.headers["X-Road-Client"]
        body = {"status": "ok", "data": {"adult": True}, "request_id": "r1", "responded_at": "2026-11-16T10:00:00Z"}
        return httpx.Response(200, json=body, headers={"X-Road-Id": "BF-1234"})

    envelope = checked(xroad_with(handler).query(CIVIL, "is-adult", AWA))
    assert seen["url"] == "http://ss-oni:8080/r1/BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL/is-adult"
    assert seen["client"] == CLIENT_ID
    assert envelope["status"] == "ok"
    assert envelope["transport_id"] == "BF-1234"


@pytest.mark.parametrize(
    ("error_type", "expected"),
    [
        ("Server.ServerProxy.AccessDenied", "refused"),
        ("Server.ServerProxy.UnknownService", "invalid_request"),
        ("Server.ServerProxy.ServiceFailed", "unavailable"),
        ("Server.ClientProxy.NetworkError", "unavailable"),
        # Codes réellement renvoyés par le banc X-Road 7.8.3
        ("server.serverproxy.access_denied", "refused"),
        ("server.serverproxy.unknown_service", "invalid_request"),
        ("server.serverproxy.service_failed.ssl_authentication_failed", "unavailable"),
    ],
)
def test_xroad_errors_are_mapped(error_type, expected):
    def handler(request):
        return httpx.Response(
            500,
            json={"type": error_type, "message": "…", "detail": "…"},
            headers={"X-Road-Error": error_type, "X-Road-Id": "BF-9"},
        )

    envelope = checked(xroad_with(handler).query(JUSTICE, "criminal-record", AWA))
    assert envelope["status"] == expected
    assert envelope["data"] is None
    assert envelope["transport_id"] == "BF-9"


def test_xroad_rejects_malformed_organization():
    envelope = checked(xroad_with(lambda r: httpx.Response(200)).query("BF/GOV/MAIRIE", "identity", AWA))
    assert envelope["status"] == "invalid_request"


def test_xroad_rejects_malformed_client_id():
    with pytest.raises(ValueError):
        XRoadConnector("http://ss", client_id="ONI")


# Choix du connecteur par l'environnement ----------------------------------------------


def test_factory_defaults_to_direct():
    connector = build_connector({})
    assert isinstance(connector, HttpRegistryConnector)
    assert connector.client_id == CLIENT_ID


def test_factory_builds_xroad():
    connector = build_connector(
        {"REGISTRY_CONNECTOR": "xroad", "XROAD_SECURITY_SERVER_URL": "http://ss-oni:8080", "REGISTRY_TIMEOUT_S": "2"}
    )
    assert isinstance(connector, XRoadConnector)
    assert connector.timeout == 2.0


def test_factory_rejects_incomplete_or_unknown_configuration():
    with pytest.raises(ValueError):
        build_connector({"REGISTRY_CONNECTOR": "xroad"})
    with pytest.raises(ValueError):
        build_connector({"REGISTRY_CONNECTOR": "carrier-pigeon"})
