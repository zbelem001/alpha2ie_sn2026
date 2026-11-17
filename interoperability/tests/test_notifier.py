"""Client NotificationClient (côté backend) : bout en bout et comportement en cas de panne."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from connectors import NotificationClient, build_notifier
from notifications.app import create_app

from .conftest import NOTIFICATION_RESPONSE_SCHEMA, SMS_REPLY_SCHEMA, assert_conforms

AWA_PHONE = "22670000001"


def checked(result: dict) -> dict:
    assert_conforms(NOTIFICATION_RESPONSE_SCHEMA, result)
    return result


def client_with(handler) -> NotificationClient:
    return NotificationClient(
        "http://notifications:8000", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


@pytest.fixture
def service() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def notifier(service) -> NotificationClient:
    def route(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "notifications"
        reply = service.request(
            request.method, request.url.path, params=request.url.params, content=request.content, headers=request.headers
        )
        return httpx.Response(reply.status_code, content=reply.content, headers=reply.headers)

    return client_with(route)


def test_consent_round_trip(notifier, service):
    sent = checked(
        notifier.send_sms(
            AWA_PHONE,
            "Dossier DOS-2026-0042 : répondez 1 pour OUI, 2 pour NON.",
            notification_id="DOS-2026-0042:consentement:1",
            reference="DOS-2026-0042",
            reply_choices=["1", "2"],
        )
    )
    assert (sent["status"], sent["duplicate"]) == ("sent", False)

    service.post("/simulate/replies", json={"sender": AWA_PHONE, "text": "1"})
    page = notifier.replies(after=0)
    assert page["status"] == "ok"
    assert [(r["text"], r["reference"]) for r in page["replies"]] == [("1", "DOS-2026-0042")]
    for item in page["replies"]:
        assert_conforms(SMS_REPLY_SCHEMA, item)
    assert notifier.replies(after=page["cursor"])["replies"] == []


def test_retry_with_same_id_is_not_sent_twice(notifier):
    first = checked(notifier.send_sms(AWA_PHONE, "Rappel", notification_id="rappel-1"))
    again = checked(notifier.send_sms(AWA_PHONE, "Rappel", notification_id="rappel-1"))
    assert (first["duplicate"], again["duplicate"], again["status"]) == (False, True, "sent")


def test_id_is_generated_when_missing(notifier):
    result = checked(notifier.send_email("awa.kabore@exemple.bf", "Dossier reçu", "Votre dossier est ouvert."))
    assert result["status"] == "sent"
    assert result["notification_id"]


def test_invalid_request_is_reported_not_raised(notifier):
    result = checked(notifier.send_sms("+226 70", "Bonjour"))
    assert result["status"] == "invalid_request"
    assert "recipient" in result["detail"]


@pytest.mark.parametrize(
    "failure",
    [
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused", request=request)),
        lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)),
        lambda request: httpx.Response(502, text="<html>Bad gateway</html>"),
        lambda request: httpx.Response(200, json={"status": "maybe"}),
        lambda request: httpx.Response(500, json={"notification_id": "x", "status": "sent", "detail": None}),
    ],
    ids=["refused", "timeout", "html-502", "unknown-status", "sent-with-500"],
)
def test_service_failures_become_unavailable(failure):
    result = checked(client_with(failure).send_sms(AWA_PHONE, "Bonjour", notification_id="n-1"))
    assert (result["status"], result["notification_id"]) == ("unavailable", "n-1")


def test_rejection_without_envelope_is_invalid_request():
    result = checked(client_with(lambda request: httpx.Response(422, text="nope")).send_sms(AWA_PHONE, "Bonjour"))
    assert result["status"] == "invalid_request"


def test_replies_when_service_is_down():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert client_with(down).replies(after=7) == {"status": "unavailable", "replies": [], "cursor": 7}


def test_build_notifier_reads_environment():
    notifier = build_notifier({"NOTIFICATION_SERVICE_URL": "http://localhost:8106/", "NOTIFICATION_TIMEOUT_S": "1.5"})
    assert (notifier.base_url, notifier.timeout) == ("http://localhost:8106", 1.5)
    default = build_notifier({})
    assert (default.base_url, default.timeout) == ("http://notifications:8000", 3.0)
