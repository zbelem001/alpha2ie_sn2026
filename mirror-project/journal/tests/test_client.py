"""Client du journal : même comportement contre le vrai service et en mémoire (MemoryJournal)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from journal_client import JournalClient, JournalUnavailable, MemoryJournal, journal_from_env

from .conftest import AWA, DEMARCHES_TOKEN, OTHER, consultation


@pytest.fixture(params=["service", "memoire"])
def journal(request, app):
    if request.param == "memoire":
        yield MemoryJournal(source="demarches")
        return
    with TestClient(app) as http:
        yield JournalClient("http://testserver", DEMARCHES_TOKEN, client=http)


def test_append_returns_the_recorded_event(journal):
    event = journal.append(consultation())
    assert event["source"] == "demarches" and event["sequence"] == 1
    assert event["question_code"] == "candidate_minimum_age" and event["consent_id"] is None
    assert journal.get(event["id"]) == event
    assert journal.get("00000000-0000-4000-8000-000000000000") is None


def test_search_filters_behave_the_same(journal):
    journal.append(consultation())
    journal.append(consultation(subject_ref=OTHER, case_id="autre", correlation_id="requete-2"))
    journal.append(consultation(event_type="consultation_contested", actor_type="citizen", outcome="open"))
    journal.append(consultation(event_type="holder_refusal", outcome="refused", purpose="Aucun accord valide"))

    assert [event["sequence"] for event in journal.search(subject_ref=AWA)] == [1, 3, 4]
    assert [event["subject_ref"] for event in journal.search(case_id="autre")] == [OTHER]
    assert len(journal.search(correlation_id="requete-1")) == 3
    assert [event["sequence"] for event in journal.search(event_type=["holder_refusal", "consultation_contested"])] == [3, 4]
    assert [event["sequence"] for event in journal.search(event_type="consultation_contested")] == [3]
    assert [event["sequence"] for event in journal.search(actor_type="citizen")] == [3]
    assert [event["sequence"] for event in journal.search(q="accord valide")] == [4]
    assert [event["sequence"] for event in journal.search(order="desc", limit=2)] == [4, 3]
    assert journal.search(requester_code="BF/GOV/FONCTION-PUBLIQUE", limit=1)[0]["sequence"] == 1


def test_date_filters(journal):
    journal.append(consultation())
    later = datetime.now(timezone.utc) + timedelta(days=365 * 10)
    assert journal.search(occurred_to=later) and not journal.search(occurred_from=later)


def test_search_follows_pages(app, monkeypatch):
    monkeypatch.setattr("journal_client.client.PAGE_SIZE", 2)
    with TestClient(app) as http:
        journal = JournalClient("http://testserver", DEMARCHES_TOKEN, client=http)
        for index in range(5):
            journal.append(consultation(correlation_id=f"requete-{index}"))
        assert [event["sequence"] for event in journal.search()] == [1, 2, 3, 4, 5]
        assert [event["sequence"] for event in journal.search(limit=3)] == [1, 2, 3]


def test_unknown_fields_are_refused_by_both(journal):
    with pytest.raises(JournalUnavailable):
        journal.append(consultation(birth_date="2004-03-12"))


def test_an_unreachable_journal_raises_instead_of_losing_the_event():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refusé", request=request)

    down = JournalClient("http://journal:8000", "jeton", client=httpx.Client(transport=httpx.MockTransport(refuse)))
    with pytest.raises(JournalUnavailable):
        down.append(consultation())
    with pytest.raises(JournalUnavailable):
        down.search(subject_ref=AWA)

    memory = MemoryJournal()
    memory.unavailable = True
    with pytest.raises(JournalUnavailable):
        memory.append(consultation())


def test_a_rejected_token_means_the_event_is_not_recorded(app):
    with TestClient(app) as http:
        with pytest.raises(JournalUnavailable):
            JournalClient("http://testserver", "inconnu-0123456789", client=http).append(consultation())


def test_configuration_from_the_environment():
    client = journal_from_env({"JOURNAL_URL": "http://journal:8000/", "JOURNAL_TOKEN": DEMARCHES_TOKEN})
    assert client.base_url == "http://journal:8000"
    with pytest.raises(JournalUnavailable):
        journal_from_env({"JOURNAL_URL": "http://journal:8000"})
