"""API du journal : inscription, recherche par citoyen, demande et date, jetons, ajout seul, chaîne."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from journal_service.app import create_app
from journal_service.security import parse_tokens

from .conftest import AUDITOR, AWA, CONSENT, DEMARCHES, OTHER, consultation


def append(client: TestClient, headers=DEMARCHES, **overrides) -> dict:
    response = client.post("/v1/events", json=consultation(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def search(client: TestClient, headers=AUDITOR, **params) -> dict:
    response = client.get("/v1/events", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_event_is_numbered_chained_and_signed_by_its_layer(client):
    first = append(client)
    second = append(client, headers=CONSENT, event_type="holder_disclosure", actor_type="administration")

    assert UUID(first["id"]) and first["sequence"] == 1 and second["sequence"] == 2
    assert first["source"] == "demarches" and second["source"] == "consentement-minimisation"
    assert first["previous_hash"] is None
    assert second["previous_hash"] == first["event_hash"]
    assert first["occurred_at"].endswith("Z")
    assert first["outcome"] == "confirmed" and first["data_categories"] == ["candidate_minimum_age"]


def test_a_layer_cannot_choose_its_source_or_add_free_fields(client):
    forged = consultation(source="registre-pirate")
    assert client.post("/v1/events", json=forged, headers=DEMARCHES).status_code == 422
    leaking = consultation(birth_date="2004-03-12")
    assert client.post("/v1/events", json=leaking, headers=DEMARCHES).status_code == 422


@pytest.mark.parametrize("overrides", [
    {"actor_type": "robot"},
    {"event_type": "Type Libre"},
    {"subject_ref": ""},
    {"purpose": ""},
    {"data_categories": [f"c{i}" for i in range(21)]},
])
def test_malformed_events_are_refused(client, overrides):
    assert client.post("/v1/events", json=consultation(**overrides), headers=DEMARCHES).status_code == 422


def test_search_by_citizen_by_request_and_by_date(client):
    append(client)  # 08:00
    append(client, subject_ref=OTHER, case_id="autre-dossier", correlation_id="requete-2")  # 08:01
    append(client, event_type="consent_revoked", outcome="revoked", correlation_id=None)  # 08:02

    by_citizen = search(client, subject_ref=AWA)["events"]
    assert [event["sequence"] for event in by_citizen] == [1, 3]

    by_case = search(client, case_id="autre-dossier")["events"]
    assert [event["subject_ref"] for event in by_case] == [OTHER]

    by_request = search(client, correlation_id="requete-1")["events"]
    assert [event["sequence"] for event in by_request] == [1]

    window = search(client, **{"from": "2026-11-18T08:01:00Z", "to": "2026-11-18T08:02:00Z"})["events"]
    assert [event["sequence"] for event in window] == [2]

    combined = search(client, subject_ref=AWA, **{"from": "2026-11-18T08:01:00+00:00"})["events"]
    assert [event["event_type"] for event in combined] == ["consent_revoked"]


def test_refusals_and_failures_are_found_like_the_rest(client):
    append(client, outcome="unavailable", purpose="Registre injoignable")
    append(client, event_type="holder_refusal", outcome="refused", purpose="Aucun accord valide pour cette question",
           headers=CONSENT)
    append(client)

    failures = search(client, event_type=["registry_check", "holder_refusal"], q="injoignable")["events"]
    assert [event["outcome"] for event in failures] == ["unavailable"]
    refusals = search(client, event_type="holder_refusal")["events"]
    assert [event["source"] for event in refusals] == ["consentement-minimisation"]
    assert search(client, q="REFUSED")["events"][0]["event_type"] == "holder_refusal"


def test_search_by_requester_and_actor(client):
    append(client)
    append(client, requester_code="BF/GOV/DIPF/PASSEPORTS", actor_type="citizen")
    assert len(search(client, requester_code="BF/GOV/DIPF/PASSEPORTS")["events"]) == 1
    assert search(client, actor_type="citizen")["events"][0]["requester_code"] == "BF/GOV/DIPF/PASSEPORTS"


def test_pages_follow_the_cursor_in_both_orders(client):
    for index in range(5):
        append(client, correlation_id=f"requete-{index}")

    first = search(client, limit=2)
    assert [event["sequence"] for event in first["events"]] == [1, 2] and first["next_after"] == 2
    second = search(client, limit=2, after=first["next_after"])
    third = search(client, limit=2, after=second["next_after"])
    assert [event["sequence"] for event in third["events"]] == [5] and third["next_after"] is None

    latest = search(client, limit=2, order="desc")
    assert [event["sequence"] for event in latest["events"]] == [5, 4]
    older = search(client, limit=10, order="desc", after=latest["next_after"])
    assert [event["sequence"] for event in older["events"]] == [3, 2, 1] and older["next_after"] is None


def test_read_one_event(client):
    event = append(client)
    assert client.get(f"/v1/events/{event['id']}", headers=AUDITOR).json() == event
    missing = client.get("/v1/events/00000000-0000-4000-8000-000000000000", headers=AUDITOR)
    assert missing.status_code == 404


def test_tokens_separate_writing_from_reading(client):
    event = consultation()
    no_token = client.post("/v1/events", json=event)
    assert no_token.status_code == 401 and no_token.headers["www-authenticate"] == "Bearer"
    assert client.post("/v1/events", json=event, headers={"Authorization": "Bearer inconnu-0123456789"}).status_code == 401
    assert client.post("/v1/events", json=event, headers=AUDITOR).status_code == 403
    assert client.get("/v1/events", headers=CONSENT).status_code == 403
    assert client.get("/v1/events").status_code == 401
    assert client.get("/v1/chain/verify", headers=CONSENT).status_code == 403


def test_without_configured_tokens_everything_is_refused(engine):
    with TestClient(create_app(engine=engine, write_tokens={}, read_tokens={})) as closed:
        assert closed.post("/v1/events", json=consultation(), headers=DEMARCHES).status_code == 401
        assert closed.get("/v1/events", headers=AUDITOR).status_code == 401


def test_there_is_no_way_to_change_or_remove_an_event(client):
    event = append(client)
    assert client.delete(f"/v1/events/{event['id']}", headers=DEMARCHES).status_code == 405
    assert client.put(f"/v1/events/{event['id']}", json=consultation(), headers=DEMARCHES).status_code == 405
    assert client.patch(f"/v1/events/{event['id']}", json={"outcome": "rejected"}, headers=DEMARCHES).status_code == 405


def test_chain_verification_detects_a_changed_or_removed_event(client, engine):
    for index in range(3):
        append(client, correlation_id=f"requete-{index}")
    intact = client.get("/v1/chain/verify", headers=AUDITOR).json()
    assert intact["valid"] is True and intact["events"] == 3 and intact["last_hash"]

    with engine.begin() as connection:
        connection.execute(text("UPDATE journal_events SET outcome = 'rejected' WHERE sequence = 2"))
    changed = client.get("/v1/chain/verify", headers=AUDITOR).json()
    assert changed == {"valid": False, "events": 2, "first_invalid_sequence": 2, "last_hash": None}

    with engine.begin() as connection:
        connection.execute(text("UPDATE journal_events SET outcome = 'confirmed' WHERE sequence = 2"))
        connection.execute(text("DELETE FROM journal_events WHERE sequence = 2"))
    removed = client.get("/v1/chain/verify", headers=AUDITOR).json()
    assert removed["valid"] is False and removed["first_invalid_sequence"] == 3


def test_token_configuration():
    assert parse_tokens("demarches=jeton-demarches-0123456789, auditeur=jeton-auditeur-0123456789") == {
        "jeton-demarches-0123456789": "demarches", "jeton-auditeur-0123456789": "auditeur",
    }
    assert parse_tokens("") == {} and parse_tokens(None) == {}
    with pytest.raises(ValueError):
        parse_tokens("jeton-sans-nom-0123456789")
    with pytest.raises(ValueError):
        parse_tokens("demarches=court")
