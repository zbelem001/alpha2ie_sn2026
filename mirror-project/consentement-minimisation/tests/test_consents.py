"""Registre des accords : décision, remplacement, retrait, expiration, journal, jetons, client."""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from consent_client import ConsentClient, ConsentRefused, ConsentServiceUnavailable, consents_from_env

from .conftest import AUTH, AWA, TOKEN, concours_consent, later


def test_a_grant_is_recorded_with_its_exact_scope_and_traced(client, journal, granted):
    assert granted["status"] == "granted" and granted["active"] is True
    assert [item["service_code"] for item in granted["scope"]] == ["is-adult", "nationality", "criminal-record"]
    [event] = journal.search(event_type="consent_recorded")
    assert event["consent_id"] == granted["id"] and event["case_id"] == "dossier-awa-1"
    assert event["subject_ref"] == AWA and event["actor_type"] == "citizen" and event["outcome"] == "granted"
    assert event["requester_name"] == "Fonction publique"
    assert event["data_categories"] == ["candidate_minimum_age", "candidate_nationality", "criminal_record_indicator"]
    assert event["purpose"] == "accord donné par le citoyen sur l'espace usager"


def test_a_new_decision_replaces_the_current_grant(client, granted):
    refused = client.post("/v1/consents", json=concours_consent(decision="refused", expires_at=None), headers=AUTH)
    assert refused.status_code == 201 and refused.json()["status"] == "refused"
    assert client.get(f"/v1/consents/{granted['id']}", headers=AUTH).json()["status"] == "revoked"
    assert client.get("/v1/consents", params={"case_id": "dossier-awa-1", "active": True}, headers=AUTH).json() == []
    history = client.get("/v1/consents", params={"case_id": "dossier-awa-1"}, headers=AUTH).json()
    assert [consent["status"] for consent in history] == ["refused", "revoked"]


def test_the_citizen_revokes_once(client, journal, granted):
    revoked = client.post(f"/v1/consents/{granted['id']}/revoke", headers=AUTH)
    assert revoked.status_code == 200 and revoked.json()["status"] == "revoked" and revoked.json()["active"] is False
    again = client.post(f"/v1/consents/{granted['id']}/revoke", headers=AUTH)
    assert again.status_code == 409
    [event] = journal.search(event_type="consent_revoked")
    assert event["consent_id"] == granted["id"] and event["outcome"] == "revoked"
    assert client.post("/v1/consents/00000000-0000-4000-8000-000000000000/revoke", headers=AUTH).status_code == 404


def test_an_expired_grant_is_no_longer_active(client, clock, granted):
    clock.now += timedelta(days=31)
    consent = client.get(f"/v1/consents/{granted['id']}", headers=AUTH).json()
    assert consent["status"] == "granted" and consent["active"] is False
    assert client.post(f"/v1/consents/{granted['id']}/revoke", headers=AUTH).status_code == 409


def test_assisted_consent_names_its_evidence(client, journal):
    simulated = concours_consent(channel="assisted", evidence_ref="consent-otp-simulated:defi-1")
    assert client.post("/v1/consents", json=simulated, headers=AUTH).status_code == 201
    assert journal.search(event_type="consent_recorded")[0]["purpose"].startswith("accord confirmé au guichet par code simulé")


@pytest.mark.parametrize("overrides", [
    {"expires_at": None},
    {"expires_at": "2026-12-18T09:00:00"},
    {"expires_at": "2026-11-17T09:00:00Z"},
    {"scope": []},
    {"channel": "sms"},
    {"scope": [concours_consent()["scope"][0], concours_consent()["scope"][0]]},
    {"scope": [{"question_code": "q", "holder_code": "BF/GOV/X", "service_code": "Pas Un Code"}]},
    {"birth_date": "2004-03-12"},
])
def test_malformed_decisions_are_refused(client, journal, overrides):
    assert client.post("/v1/consents", json=concours_consent(**overrides), headers=AUTH).status_code == 422
    assert journal.events == []


def test_without_the_journal_nothing_is_recorded(client, journal):
    journal.unavailable = True
    assert client.post("/v1/consents", json=concours_consent(), headers=AUTH).status_code == 503
    journal.unavailable = False
    assert client.get("/v1/consents", params={"case_id": "dossier-awa-1"}, headers=AUTH).json() == []


def test_the_consent_registry_requires_the_service_token(client):
    assert client.post("/v1/consents", json=concours_consent()).status_code == 401
    assert client.get("/v1/consents", params={"case_id": "x"}, headers={"Authorization": "Bearer inconnu-0123456789"}).status_code == 401
    assert client.get("/v1/consents", headers=AUTH).status_code == 422


def test_client_round_trip(app):
    with TestClient(app) as http:
        consents = ConsentClient("http://testserver", TOKEN, client=http)
        grant = consents.record(concours_consent(expires_at=later(30)))
        assert consents.active("dossier-awa-1")["id"] == grant["id"]
        assert consents.get(grant["id"])["status"] == "granted"
        assert consents.get("00000000-0000-4000-8000-000000000000") is None
        assert consents.revoke(grant["id"])["status"] == "revoked"
        assert consents.active("dossier-awa-1") is None
        with pytest.raises(ConsentRefused) as refused:
            consents.revoke(grant["id"])
        assert refused.value.status_code == 409
        assert [item["status"] for item in consents.search(subject_ref=AWA)] == ["revoked"]


def test_client_failures():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refusé", request=request)

    consents = ConsentClient("http://consentement:8000", TOKEN, client=httpx.Client(transport=httpx.MockTransport(down)))
    with pytest.raises(ConsentServiceUnavailable):
        consents.active("dossier")
    with pytest.raises(ConsentServiceUnavailable):
        consents_from_env({"CONSENT_URL": "http://consentement:8000"})
    assert consents_from_env({"CONSENT_URL": "http://c:8000/", "CONSENT_TOKEN": TOKEN}).base_url == "http://c:8000"
