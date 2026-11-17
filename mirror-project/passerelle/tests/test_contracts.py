"""Les exemples publiés dans contracts/examples restent conformes aux schémas."""

import json

from .conftest import CONTRACTS, REQUEST_SCHEMA, RESPONSE_SCHEMA, assert_conforms


def test_published_examples_match_schemas():
    examples = json.loads((CONTRACTS / "examples" / "registry-exchanges.json").read_text(encoding="utf-8"))
    assert examples["examples"]
    for example in examples["examples"]:
        assert_conforms(REQUEST_SCHEMA, example["payload"])
        assert_conforms(RESPONSE_SCHEMA, example["response"])
        assert example["response"]["organization"] == example["organization"]
        assert example["response"]["service"] == example["service"]


def test_schema_forbids_data_outside_ok():
    leaking = {
        "request_id": None,
        "organization": "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
        "service": "identity",
        "status": "ambiguous",
        "data": {"candidates": []},
        "message": None,
        "responded_at": "2026-11-16T10:00:00Z",
    }
    assert list(RESPONSE_SCHEMA.iter_errors(leaking))


def test_notification_examples_match_schemas():
    from .conftest import NOTIFICATION_REQUEST_SCHEMA, NOTIFICATION_RESPONSE_SCHEMA, SMS_REPLY_SCHEMA

    examples = json.loads((CONTRACTS / "examples" / "notification-exchanges.json").read_text(encoding="utf-8"))
    assert examples["sends"] and examples["replies"]
    for example in examples["sends"]:
        assert_conforms(NOTIFICATION_REQUEST_SCHEMA, example["request"])
        assert_conforms(NOTIFICATION_RESPONSE_SCHEMA, example["response"])
        assert example["response"]["notification_id"] == example["request"]["notification_id"]
    for example in examples["replies"]:
        assert_conforms(SMS_REPLY_SCHEMA, example["reply"])


def test_notification_examples_match_the_simulator():
    """Les exemples d'envoi rejoués sur le service donnent le statut et le code HTTP annoncés."""
    from fastapi.testclient import TestClient

    from notifications.app import create_app

    service = TestClient(create_app())
    examples = json.loads((CONTRACTS / "examples" / "notification-exchanges.json").read_text(encoding="utf-8"))
    for example in examples["sends"]:
        if example["http_status"] is None:
            continue
        response = service.post("/notifications", json=example["request"])
        assert response.status_code == example["http_status"], example["title"]
        assert response.json()["status"] == example["response"]["status"], example["title"]
        assert response.json()["detail"] == example["response"]["detail"], example["title"]
