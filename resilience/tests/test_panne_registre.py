"""Épreuve « tenir quand un registre tombe » : statut clair, jamais « oui », consultation au journal,
puis reprise automatique sans appel en double."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api import CitizenCaseCreate, execute_checks, revoke_consent, start_citizen_case
from app.database.models import RegistryRequest, RequestAttempt
from app.retry import retry_unavailable_checks

from .conftest import AGENT, CITIZEN, CONCOURS

JUSTICE_QUESTIONS = {"candidate_nationality", "criminal_record_indicator"}


def start_concours(stack) -> dict:
    with stack.db() as db:
        return start_citizen_case(CitizenCaseCreate(procedure_code=CONCOURS, confirmed=True), CITIZEN, db)


def statuses(case: dict) -> dict[str, str]:
    return {check["question_code"]: check["status"] for check in case["checks"]}


def outcomes(stack, case_id: str, event_type: str) -> list[tuple[str, str]]:
    return [(event["question_code"], event["outcome"])
            for event in stack.journal.search(case_id=case_id, event_type=event_type)]


def test_a_registry_down_gives_a_clear_status_never_yes(stack):
    stack.registries["justice"].down = True
    case = start_concours(stack)

    assert case["status"] == "pending"
    assert statuses(case) == {"candidate_minimum_age": "confirmed", "candidate_nationality": "unavailable",
                              "criminal_record_indicator": "unavailable"}
    assert all(check["result"] is None for check in case["checks"] if check["question_code"] in JUSTICE_QUESTIONS)
    # Chaque tentative figure au journal, des deux côtés : demandeur et détenteur.
    assert sorted(outcomes(stack, case["id"], "registry_check")) == [
        ("candidate_minimum_age", "confirmed"), ("candidate_nationality", "unavailable"),
        ("criminal_record_indicator", "unavailable")]
    assert sorted(outcomes(stack, case["id"], "holder_response")) == [
        ("candidate_minimum_age", "ok"), ("candidate_nationality", "unavailable"),
        ("criminal_record_indicator", "unavailable")]


def test_checks_resume_automatically_without_duplicate_calls(stack):
    justice = stack.registries["justice"]
    justice.down = True
    case = start_concours(stack)
    justice.down = False

    assert retry_unavailable_checks(stack.sessions) == [case["id"]]
    with stack.db() as db:
        requests = db.scalars(select(RegistryRequest).where(RegistryRequest.case_id == UUID(case["id"]))).all()
        assert {request.status for request in requests} == {"confirmed"}
        justice_ids = {str(request.id) for request in requests if request.attempt_count == 2}
        attempts = db.scalars(select(RequestAttempt).where(
            RequestAttempt.registry_request_id.in_([UUID(item) for item in justice_ids])
        ).order_by(RequestAttempt.attempt_number)).all()
    # Une tentative échouée pendant la panne, une réussie après : jamais deux appels réussis.
    assert sorted(justice.calls) == sorted([*justice_ids, *justice_ids])
    assert [attempt.status for attempt in attempts].count("succeeded") == 2
    events = outcomes(stack, case["id"], "registry_check")
    for question in JUSTICE_QUESTIONS:
        assert [outcome for code, outcome in events if code == question] == ["unavailable", "confirmed"]
    # Plus rien à reprendre : aucun nouvel appel.
    assert retry_unavailable_checks(stack.sessions) == []
    assert len(justice.calls) == 4


def test_a_slow_registry_is_unavailable_and_resumed(stack):
    stack.registries["justice"].slow = True
    case = start_concours(stack)
    assert statuses(case)["candidate_nationality"] == "unavailable"
    stack.registries["justice"].slow = False
    retry_unavailable_checks(stack.sessions)
    with stack.db() as db:
        assert {request.status for request in db.scalars(select(RegistryRequest))} == {"confirmed"}


def test_a_non_conforming_answer_never_becomes_yes(stack):
    stack.registries["justice"].reply = httpx.Response(200, json={"status": "ok", "data": {"burkinabe": "oui"}})
    case = start_concours(stack)
    assert statuses(case)["candidate_nationality"] == "unavailable"
    assert case["status"] == "pending"


def test_no_automatic_retry_without_an_active_consent(stack):
    justice = stack.registries["justice"]
    justice.down = True
    case = start_concours(stack)
    with stack.db() as db:
        revoke_consent(UUID(case["id"]), CITIZEN, db)
    justice.down = False
    calls_before, events_before = len(justice.calls), len(stack.journal.events)

    assert retry_unavailable_checks(stack.sessions) == []
    assert len(justice.calls) == calls_before
    assert len(stack.journal.events) == events_before  # aucun « checks_blocked » répété


def test_an_interrupted_call_is_taken_over_after_its_lease(stack):
    """Journal injoignable au moment d'inscrire la réponse : rien ne sort, la demande est reprise ensuite."""
    stack.registries["justice"].down = True
    case = start_concours(stack)
    stack.registries["justice"].down = False
    stack.journal.unavailable = True
    with stack.db() as db, pytest.raises(HTTPException) as error:
        execute_checks(UUID(case["id"]), AGENT, db)
    assert error.value.status_code == 503
    stack.journal.unavailable = False

    with stack.db() as db:
        pending = [request for request in db.scalars(select(RegistryRequest)) if request.status != "confirmed"]
        assert pending  # restées en attente, pas confirmées sans trace
        for request in pending:
            request.updated_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        db.commit()
    retry_unavailable_checks(stack.sessions)
    with stack.db() as db:
        assert {request.status for request in db.scalars(select(RegistryRequest))} == {"confirmed"}


def test_without_the_consent_registry_no_registry_is_called(stack):
    stack.registries["justice"].down = True
    case = start_concours(stack)
    stack.registries["justice"].down = False
    calls = {slug: len(registry.calls) for slug, registry in stack.registries.items()}

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refusé", request=request)

    from consent_client import ConsentClient
    from app.consents import use_consents
    use_consents(ConsentClient("http://consentement:8000", "jeton", client=httpx.Client(transport=httpx.MockTransport(down))))
    with stack.db() as db, pytest.raises(HTTPException) as error:
        execute_checks(UUID(case["id"]), AGENT, db)
    assert error.value.status_code == 503
    assert retry_unavailable_checks(stack.sessions) == []
    assert {slug: len(registry.calls) for slug, registry in stack.registries.items()} == calls
