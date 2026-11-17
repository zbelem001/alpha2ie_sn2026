"""Les exemples publiés dans passerelle/examples restent conformes aux schémas de passerelle/schemas.

Les exemples d'échanges avec les registres sont vérifiés dans registres/tests/test_contracts.py.
"""

import json

from .conftest import LAYER, assert_conforms


def test_notification_examples_match_schemas():
    from .conftest import NOTIFICATION_REQUEST_SCHEMA, NOTIFICATION_RESPONSE_SCHEMA, SMS_REPLY_SCHEMA

    examples = json.loads((LAYER / "examples" / "notification-exchanges.json").read_text(encoding="utf-8"))
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
    examples = json.loads((LAYER / "examples" / "notification-exchanges.json").read_text(encoding="utf-8"))
    for example in examples["sends"]:
        if example["http_status"] is None:
            continue
        response = service.post("/notifications", json=example["request"])
        assert response.status_code == example["http_status"], example["title"]
        assert response.json()["status"] == example["response"]["status"], example["title"]
        assert response.json()["detail"] == example["response"]["detail"], example["title"]
