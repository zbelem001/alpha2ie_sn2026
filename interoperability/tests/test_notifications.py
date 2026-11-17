"""Service de notifications simulé : envoi, idempotence, réponses du citoyen, webhook, pages."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from notifications.app import create_app

from .conftest import (
    NOTIFICATION_REQUEST_SCHEMA,
    NOTIFICATION_RESPONSE_SCHEMA,
    SMS_REPLY_SCHEMA,
    assert_conforms,
)

AWA_PHONE = "22670000001"
CONSENT_SMS = {
    "notification_id": "DOS-2026-0042:consentement:1",
    "channel": "sms",
    "recipient": AWA_PHONE,
    "message": "Dossier DOS-2026-0042 : la Fonction publique demande à vérifier 3 informations. "
    "Répondez 1 pour OUI, 2 pour NON.",
    "reference": "DOS-2026-0042",
    "reply_choices": ["1", "2"],
}


def send(client: TestClient, payload: dict[str, Any], *, valid: bool = True) -> tuple[int, dict[str, Any]]:
    """Envoie une demande, vérifie la conformité de la demande (si valide) et de la réponse."""
    if valid:
        assert_conforms(NOTIFICATION_REQUEST_SCHEMA, payload)
    else:
        assert list(NOTIFICATION_REQUEST_SCHEMA.iter_errors(payload)), "le schéma devrait refuser cette demande"
    response = client.post("/notifications", json=payload)
    body = response.json()
    assert_conforms(NOTIFICATION_RESPONSE_SCHEMA, body)
    return response.status_code, body


def reply(client: TestClient, text: str, *, sender: str = AWA_PHONE, in_reply_to: str | None = None):
    return client.post("/simulate/replies", json={"sender": sender, "text": text, "in_reply_to": in_reply_to})


@pytest.fixture
def notifications() -> TestClient:
    return TestClient(create_app())


# Envoi ---------------------------------------------------------------------------------


def test_sms_is_delivered_to_the_simulated_phone(notifications):
    status, body = send(notifications, CONSENT_SMS)
    assert status == 201
    assert body["status"] == "sent"
    assert body["notification_id"] == CONSENT_SMS["notification_id"]
    assert body["duplicate"] is False

    thread = notifications.get(f"/simulate/phones/{AWA_PHONE}/thread").json()["items"]
    assert [item["message"] for item in thread] == [CONSENT_SMS["message"]]
    assert thread[0]["reply_choices"] == ["1", "2"]
    assert thread[0]["answered"] is False


def test_email_is_delivered(notifications):
    status, body = send(
        notifications,
        {
            "notification_id": "DOS-2026-0042:recu",
            "channel": "email",
            "recipient": "awa.kabore@exemple.bf",
            "subject": "Dossier DOS-2026-0042 reçu",
            "message": "Votre dossier a bien été ouvert.",
        },
    )
    assert (status, body["status"]) == (201, "sent")
    stored = notifications.get("/notifications/DOS-2026-0042:recu").json()
    assert stored["subject"] == "Dossier DOS-2026-0042 reçu"


@pytest.mark.parametrize(
    ("channel", "recipient"), [("sms", "22670000099"), ("email", "injoignable@exemple.bf")]
)
def test_unreachable_recipient_fails_and_never_reaches_a_phone(notifications, channel, recipient):
    payload = {"notification_id": f"echec-{channel}", "channel": channel, "recipient": recipient, "message": "Test"}
    if channel == "email":
        payload["subject"] = "Test"
    status, body = send(notifications, payload)
    assert (status, body["status"]) == (201, "failed")
    assert notifications.get("/simulate/phones/22670000099/thread").json()["items"] == []


def test_resending_the_same_notification_id_sends_nothing_twice(notifications):
    send(notifications, CONSENT_SMS)
    status, body = send(notifications, CONSENT_SMS)
    assert (status, body["status"], body["duplicate"]) == (200, "sent", True)
    assert len(notifications.get("/notifications", params={"recipient": AWA_PHONE}).json()["notifications"]) == 1


def test_reusing_a_notification_id_for_another_message_is_refused(notifications):
    send(notifications, CONSENT_SMS)
    status, body = send(notifications, {**CONSENT_SMS, "message": "Autre texte"})
    assert (status, body["status"]) == (409, "invalid_request")


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"recipient": "+226 70 00 00 01"}, "recipient"),
        ({"message": "x" * 481}, "480"),
        ({"subject": "Objet"}, "subject"),
        ({"reply_choices": ["1", "1"]}, "double"),
        ({"reply_choices": ["oui !"]}, "reply_choices"),
        ({"message": "Acte ACTE:OUAGA:2004:01234 vérifié"}, "identifiant pivot"),
        ({"channel": "fax"}, "channel"),
        ({"notification_id": "a b"}, "notification_id"),
        ({"unexpected": True}, "unexpected"),
    ],
)
def test_invalid_requests_are_refused_without_echoing_the_message(notifications, change, fragment):
    payload = {**CONSENT_SMS, **change}
    status, body = send(notifications, payload, valid=False)
    assert (status, body["status"]) == (400, "invalid_request")
    assert fragment in body["detail"]
    assert "ACTE:OUAGA" not in body["detail"]
    assert notifications.get("/notifications").json()["notifications"] == []


def test_email_cannot_offer_reply_choices(notifications):
    payload = {
        "notification_id": "mail-choix",
        "channel": "email",
        "recipient": "awa.kabore@exemple.bf",
        "message": "Répondez 1 ou 2",
        "reply_choices": ["1", "2"],
    }
    status, body = send(notifications, payload, valid=False)
    assert (status, body["status"]) == (400, "invalid_request")


def test_missing_or_unreadable_body(notifications):
    response = notifications.post("/notifications", content=b"pas du json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert_conforms(NOTIFICATION_RESPONSE_SCHEMA, response.json())
    assert response.json()["notification_id"] is None

    response = notifications.post("/notifications", json={"channel": "sms"})
    assert response.status_code == 400
    assert response.json()["status"] == "invalid_request"


def test_consultation_filters(notifications):
    send(notifications, CONSENT_SMS)
    send(notifications, {**CONSENT_SMS, "notification_id": "autre", "recipient": "22670000002", "reference": "DOS-2"})
    by_reference = notifications.get("/notifications", params={"reference": "DOS-2026-0042"}).json()
    assert [n["notification_id"] for n in by_reference["notifications"]] == [CONSENT_SMS["notification_id"]]
    assert notifications.get("/notifications/inconnu").status_code == 404


# Réponses du citoyen -------------------------------------------------------------------


def test_citizen_reply_is_linked_to_the_sms_and_its_reference(notifications):
    send(notifications, CONSENT_SMS)
    response = reply(notifications, " 1 ", in_reply_to=CONSENT_SMS["notification_id"])
    assert response.status_code == 201
    recorded = response.json()["reply"]
    assert_conforms(SMS_REPLY_SCHEMA, recorded)
    assert recorded["text"] == "1"
    assert recorded["in_reply_to"] == CONSENT_SMS["notification_id"]
    assert recorded["reference"] == "DOS-2026-0042"
    assert response.json()["webhook"]["status"] == "disabled"

    thread = notifications.get(f"/simulate/phones/{AWA_PHONE}/thread").json()["items"]
    assert [item["kind"] for item in thread] == ["sms", "reply"]
    assert thread[0]["answered"] is True


def test_free_text_reply_goes_to_the_last_sms_with_choices(notifications):
    send(notifications, CONSENT_SMS)
    send(notifications, {**CONSENT_SMS, "notification_id": "info", "reply_choices": None, "message": "Information"})
    recorded = reply(notifications, "OUI").json()["reply"]
    assert recorded["in_reply_to"] == CONSENT_SMS["notification_id"]


def test_reply_without_any_sms_has_no_target(notifications):
    recorded = reply(notifications, "Bonjour").json()["reply"]
    assert (recorded["in_reply_to"], recorded["reference"]) == (None, None)


def test_cannot_reply_to_someone_elses_sms(notifications):
    send(notifications, CONSENT_SMS)
    response = reply(notifications, "1", sender="22670000002", in_reply_to=CONSENT_SMS["notification_id"])
    assert response.status_code == 400


@pytest.mark.parametrize("body", [{"sender": "abc", "text": "1"}, {"sender": AWA_PHONE, "text": ""}, {"sender": AWA_PHONE}])
def test_invalid_simulated_reply(notifications, body):
    assert notifications.post("/simulate/replies", json=body).status_code == 400


def test_replies_can_be_polled_with_a_cursor(notifications):
    send(notifications, CONSENT_SMS)
    reply(notifications, "1")
    first = notifications.get("/replies").json()
    assert len(first["replies"]) == 1
    for item in first["replies"]:
        assert_conforms(SMS_REPLY_SCHEMA, item)

    assert notifications.get("/replies", params={"after": first["cursor"]}).json() == {
        "replies": [],
        "cursor": first["cursor"],
    }
    reply(notifications, "2")
    later = notifications.get("/replies", params={"after": first["cursor"]}).json()
    assert [r["text"] for r in later["replies"]] == ["2"]


# Webhook vers le backend ---------------------------------------------------------------


def app_with_webhook(handler) -> TestClient:
    return TestClient(
        create_app(
            webhook_url="http://backend:8000/webhooks/sms-replies",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
    )


def test_reply_is_pushed_to_the_backend_webhook():
    received: list[dict[str, Any]] = []

    def backend(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        return httpx.Response(204)

    client = app_with_webhook(backend)
    send(client, CONSENT_SMS)
    response = reply(client, "1", in_reply_to=CONSENT_SMS["notification_id"])
    assert response.json()["webhook"]["status"] == "delivered"
    assert len(received) == 1
    assert_conforms(SMS_REPLY_SCHEMA, received[0])
    assert received[0]["reference"] == "DOS-2026-0042"


@pytest.mark.parametrize("failure", ["down", "error"])
def test_backend_down_keeps_the_reply_for_polling(failure):
    def backend(request: httpx.Request) -> httpx.Response:
        if failure == "down":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(503)

    client = app_with_webhook(backend)
    send(client, CONSENT_SMS)
    response = reply(client, "1")
    assert response.status_code == 201
    assert response.json()["webhook"]["status"] == "failed"
    assert [r["text"] for r in client.get("/replies").json()["replies"]] == ["1"]


# Démonstration et confidentialité ------------------------------------------------------


def test_reset_empties_everything(notifications):
    send(notifications, CONSENT_SMS)
    reply(notifications, "1")
    assert notifications.post("/simulate/reset").status_code == 204
    assert notifications.get("/notifications").json()["notifications"] == []
    assert notifications.get("/replies").json()["replies"] == []
    # Après remise à zéro, le même identifiant peut resservir.
    assert send(notifications, CONSENT_SMS)[0] == 201


def test_demo_pages(notifications):
    outbox = notifications.get("/")
    assert outbox.status_code == 200
    assert "Boîte d'envoi simulée" in outbox.text
    phone = notifications.get(f"/phone/{AWA_PHONE}")
    assert phone.status_code == 200
    assert f'data-number="{AWA_PHONE}"' in phone.text
    assert notifications.get("/phone/<script>").status_code == 404
    assert notifications.get("/simulate/phones/abc/thread").status_code == 404


def test_logs_never_contain_the_message_or_the_full_number(notifications, caplog):
    with caplog.at_level(logging.INFO, logger="notifications"):
        send(notifications, CONSENT_SMS)
        reply(notifications, "1")
    logs = caplog.text
    assert "notification=DOS-2026-0042:consentement:1" in logs
    assert AWA_PHONE not in logs
    assert "Répondez" not in logs
