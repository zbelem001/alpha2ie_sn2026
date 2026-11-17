from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import connectors
from app.api import (
    CaseCreate,
    ConsentCreate,
    IdentityLinkCreate,
    create_case,
    execute_checks,
    link_citizen_identity,
    list_notifications,
    mark_notification_read,
    record_consent,
    revoke_consent,
)
from app.database.base import Base
from app.database.models import (
    Administration,
    AuditEvent,
    Case,
    CitizenIdentityLink,
    Consent,
    Notification,
    Permission,
    Procedure,
    ProcedureQuestion,
    Question,
    Registry,
    RegistryRequest,
    RequestAttempt,
)
from app.security import Principal


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_procedure(db: Session) -> tuple[Administration, Administration, Procedure]:
    owner = Administration(code="BF/GOV/DIPF/PASSEPORTS", name="Passeports")
    other = Administration(code="BF/GOV/FONCTION-PUBLIQUE", name="Fonction publique")
    db.add_all([owner, other])
    db.flush()

    registry = Registry(administration_id=owner.id, code="main")
    db.add(registry)
    db.flush()

    question = Question(
        code="passport_cnib_valid",
        registry_id=registry.id,
        service_code="cnib-status",
        response_key="valid",
        description="Vérifier le statut de la CNIB",
    )
    db.add(question)
    db.flush()

    procedure = Procedure(
        code="passeport_ordinaire_precheck",
        owner_administration_id=owner.id,
        title="Passeport adulte",
        config_version=1,
    )
    db.add(procedure)
    db.flush()
    db.add(ProcedureQuestion(procedure_id=procedure.id, question_id=question.id, required=True, position=1))
    db.add(Permission(requester_administration_id=owner.id, question_id=question.id, active=True))
    db.commit()
    return owner, other, procedure


def test_agent_cannot_open_another_administrations_procedure(db: Session):
    _, other, procedure = add_procedure(db)
    principal = Principal(
        subject="agent-sub",
        roles=frozenset({"agent"}),
        administration_code=other.code,
        citizen_ref=None,
    )

    with pytest.raises(HTTPException) as error:
        create_case(CaseCreate(procedure_code=procedure.code, subject_ref="ACTE:OUAGA:2004:01234"), principal, db)

    assert error.value.status_code == 403
    assert db.scalar(select(func.count()).select_from(Case)) == 0


def test_agent_can_open_its_own_administrations_procedure(db: Session):
    owner, _, procedure = add_procedure(db)
    principal = Principal(
        subject="agent-sub",
        roles=frozenset({"agent"}),
        administration_code=owner.code,
        citizen_ref=None,
    )

    result = create_case(CaseCreate(procedure_code=procedure.code, subject_ref="ACTE:OUAGA:2004:01234"), principal, db)

    assert result["procedure_code"] == procedure.code
    assert result["status"] == "received"
    assert db.scalar(select(func.count()).select_from(Case)) == 1


def test_case_creation_notifies_citizen_and_keeps_sms_simulated(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    monkeypatch.setenv("SMS_PROVIDER", "simulated")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    case_id = UUID(case["id"])

    notifications = db.scalars(
        select(Notification).where(Notification.case_id == case_id).order_by(Notification.channel)
    ).all()
    assert [(item.channel, item.delivery_status) for item in notifications] == [
        ("platform", "delivered"), ("sms", "simulated")
    ]
    assert all(item.recipient_ref == citizen.citizen_ref for item in notifications)
    assert all("Connectez-vous à la plateforme" in item.message for item in notifications)
    assert all("consentement" in item.message for item in notifications)

    visible = list_notifications(citizen, db)
    assert len(visible) == 1
    assert visible[0]["case_id"] == str(case_id)
    assert visible[0]["read_at"] is None

    stranger = Principal("other-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:99999")
    assert list_notifications(stranger, db) == []
    with pytest.raises(HTTPException) as error:
        mark_notification_read(UUID(visible[0]["id"]), stranger, db)
    assert error.value.status_code == 404

    marked = mark_notification_read(UUID(visible[0]["id"]), citizen, db)
    assert marked["read_at"] is not None


def test_case_creation_dispatches_twilio_for_configured_demo_citizen(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    monkeypatch.setenv("SMS_PROVIDER", "twilio")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC" + "1" * 32)
    monkeypatch.setenv("TWILIO_API_KEY_SID", "SK" + "2" * 32)
    monkeypatch.setenv("TWILIO_API_KEY_SECRET", "test-secret")
    monkeypatch.setenv("TWILIO_MESSAGING_SERVICE_SID", "MG" + "3" * 32)
    monkeypatch.setenv("TWILIO_DEMO_CITIZEN_REF", citizen.citizen_ref)
    monkeypatch.setenv("TWILIO_DEMO_TO", "+22670000000")
    db.add(CitizenIdentityLink(
        principal_sub=citizen.subject,
        subject_ref=citizen.citizen_ref,
        phone_number="+22670000001",
    ))
    db.commit()
    sent = {}

    def fake_send(settings, to_number, body):
        sent.update(to=to_number, body=body)
        return "SM" + "4" * 32

    monkeypatch.setattr("app.sms.send_twilio_sms", fake_send)
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    sms = db.scalar(select(Notification).where(
        Notification.case_id == UUID(case["id"]), Notification.channel == "sms"
    ))

    assert sms.delivery_status == "sent"
    assert sms.provider_message_id == "SM" + "4" * 32
    assert sms.delivery_error is None
    assert sent["to"] == "+22670000001"
    assert "Connectez-vous à la plateforme" in sent["body"]


def test_citizen_can_link_confirmed_reference_with_verified_phone(db: Session, monkeypatch):
    citizen = Principal(
        "citizen-sub", frozenset({"citizen"}), None, None,
        phone_number="+22670000099", phone_number_verified=True,
    )

    class IdentityConnector:
        def query(self, organization, service, payload):
            assert organization == "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
            assert service == "identity"
            return {"status": "ok", "data": {"pivot_id": payload["subject"]["pivot_id"]}}

    monkeypatch.setattr(connectors, "build_connector", lambda: IdentityConnector())
    result = link_citizen_identity(
        IdentityLinkCreate(subject_ref="acte:ouaga:2004:01234", confirmed=True),
        citizen,
        db,
    )

    assert result == {"linked": True, "subject_ref": "ACTE:OUAGA:2004:01234"}
    stored = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == citizen.subject))
    assert stored.subject_ref == "ACTE:OUAGA:2004:01234"
    assert stored.phone_number == "+22670000099"


def test_citizen_identity_link_requires_confirmation_and_verified_phone(db: Session):
    unverified = Principal("citizen-sub", frozenset({"citizen"}), None, None, "+22670000099", False)
    with pytest.raises(HTTPException) as unchecked:
        link_citizen_identity(IdentityLinkCreate(subject_ref="ACTE:OUAGA:2004:01234", confirmed=False), unverified, db)
    assert unchecked.value.status_code == 422

    with pytest.raises(HTTPException) as no_verified_phone:
        link_citizen_identity(IdentityLinkCreate(subject_ref="ACTE:OUAGA:2004:01234", confirmed=True), unverified, db)
    assert no_verified_phone.value.status_code == 403


def test_sms_cannot_be_recorded_as_consent_channel():
    with pytest.raises(ValidationError):
        ConsentCreate(
            decision="granted",
            question_codes=["passport_cnib_valid"],
            notice_version="demo-1",
            channel="sms",
        )


def test_refusal_replaces_prior_grant_and_a_later_grant_resumes_checks(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    case_id = UUID(case["id"])
    question_codes = ["passport_cnib_valid"]

    granted = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=question_codes, notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    assert granted["expires_at"] - granted["granted_at"] == timedelta(days=30)
    refused = record_consent(
        case_id,
        ConsentCreate(decision="refused", question_codes=question_codes, notice_version="demo-1", channel="web"),
        citizen,
        db,
    )

    old_consent = db.get(Consent, UUID(granted["id"]))
    assert old_consent.status == "revoked"
    assert refused["status"] == "refused"
    with pytest.raises(HTTPException) as error:
        execute_checks(case_id, agent, db)
    assert error.value.status_code == 403
    request = db.scalar(select(RegistryRequest).where(RegistryRequest.case_id == case_id))
    assert request.status == "queued"

    renewed = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=question_codes, notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    # SQLite does not preserve timezone-aware datetimes. The duration is checked
    # above; clear expiry here to exercise the grant/resume path independently.
    db.get(Consent, UUID(renewed["id"])).expires_at = None

    class SuccessfulConnector:
        def query(self, organization, service, payload):
            return {"status": "ok", "data": {"valid": True}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: SuccessfulConnector())
    result = execute_checks(case_id, agent, db)

    assert result["status"] == "completed"
    assert result["checks"][0]["status"] == "confirmed"
    assert result["checks"][0]["attempt_count"] == 1


def test_only_the_case_citizen_can_record_consent(db: Session):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    stranger = Principal("stranger-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:99999")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)

    with pytest.raises(HTTPException) as error:
        record_consent(
            UUID(case["id"]),
            ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"],
                          notice_version="demo-1", channel="web"),
            stranger,
            db,
        )

    assert error.value.status_code == 403
    assert db.scalar(select(func.count()).select_from(Consent)) == 0


@pytest.mark.parametrize(
    "expires_at",
    [
        datetime.now(timezone.utc) - timedelta(seconds=1),
        datetime.now(timezone.utc) + timedelta(days=31),
        datetime.now(),
    ],
    ids=["past", "over-30-days", "timezone-missing"],
)
def test_consent_expiration_must_be_future_timezone_aware_and_within_30_days(db: Session, expires_at):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)

    with pytest.raises(HTTPException) as error:
        record_consent(
            UUID(case["id"]),
            ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"],
                          notice_version="demo-1", channel="web", expires_at=expires_at),
            citizen,
            db,
        )

    assert error.value.status_code == 422
    assert db.scalar(select(func.count()).select_from(Consent)) == 0


def test_citizen_can_revoke_consent_and_audit_hashes_form_a_chain(db: Session):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    stranger = Principal("stranger-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:99999")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    case_id = UUID(case["id"])
    consent = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"],
                      notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    # SQLite drops timezone metadata; revoke checks status and ownership here.
    db.get(Consent, UUID(consent["id"])).expires_at = None

    with pytest.raises(HTTPException) as error:
        revoke_consent(case_id, stranger, db)
    assert error.value.status_code == 403

    result = revoke_consent(case_id, citizen, db)

    assert result["status"] == "revoked"
    assert db.get(Consent, UUID(consent["id"])).status == "revoked"
    with pytest.raises(HTTPException) as error:
        execute_checks(case_id, agent, db)
    assert error.value.status_code == 403
    request = db.scalar(select(RegistryRequest).where(RegistryRequest.case_id == case_id))
    assert request.status == "queued"

    events = db.scalars(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.occurred_at)
    ).all()
    assert [event.event_type for event in events] == [
        "case_created", "consent_requested", "consent_recorded", "consent_revoked", "checks_blocked"
    ]
    assert events[0].previous_hash is None
    for previous, current in zip(events, events[1:]):
        assert current.previous_hash == previous.event_hash
        assert current.event_hash


@pytest.mark.parametrize(
    ("response_value", "expected_check_status", "expected_case_status", "expected_result"),
    [
        ("false", "error", "pending", None),
        (False, "rejected", "rejected", {"valid": False}),
    ],
)
def test_registry_boolean_must_be_a_boolean(
    db: Session,
    monkeypatch,
    response_value,
    expected_check_status,
    expected_case_status,
    expected_result,
):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    case_id = UUID(case["id"])
    consent = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"], notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    # SQLite drops timezone metadata on reads; expiry was covered in the test above.
    db.get(Consent, UUID(consent["id"])).expires_at = None

    class RegistryConnector:
        def query(self, organization, service, payload):
            return {"status": "ok", "data": {"valid": response_value}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: RegistryConnector())
    result = execute_checks(case_id, agent, db)

    check = result["checks"][0]
    request = db.scalar(select(RegistryRequest).where(RegistryRequest.case_id == case_id))
    assert result["status"] == expected_case_status
    assert check["status"] == expected_check_status
    assert request.minimal_result == expected_result
    if expected_check_status == "error":
        assert request.attempt_count == 1


def test_unavailable_registry_can_be_retried_without_duplicate_request(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    case_id = UUID(case["id"])
    consent = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"], notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    db.get(Consent, UUID(consent["id"])).expires_at = None

    class IntermittentConnector:
        attempts = 0

        def query(self, organization, service, payload):
            self.attempts += 1
            if self.attempts == 1:
                raise TimeoutError("registre hors ligne")
            return {"status": "ok", "data": {"valid": True}, "transport_id": "retry-succeeded"}

    connector = IntermittentConnector()
    monkeypatch.setattr(connectors, "build_connector", lambda: connector)

    first = execute_checks(case_id, agent, db)
    assert first["status"] == "pending"
    assert first["checks"][0]["status"] == "unavailable"
    request = db.scalar(select(RegistryRequest).where(RegistryRequest.case_id == case_id))
    request_id = request.id
    idempotency_key = request.idempotency_key

    second = execute_checks(case_id, agent, db)

    assert second["status"] == "completed"
    assert second["checks"][0]["status"] == "confirmed"
    assert second["checks"][0]["attempt_count"] == 2
    assert db.scalar(select(func.count()).select_from(RegistryRequest).where(RegistryRequest.case_id == case_id)) == 1
    assert request.id == request_id
    assert request.idempotency_key == idempotency_key
    attempts = db.scalars(
        select(RequestAttempt).where(RequestAttempt.registry_request_id == request_id).order_by(RequestAttempt.attempt_number)
    ).all()
    assert [attempt.attempt_number for attempt in attempts] == [1, 2]
    assert [attempt.status for attempt in attempts] == ["failed", "succeeded"]


def test_fresh_pending_claim_is_skipped_and_stale_claim_is_recovered(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    case_id = UUID(case["id"])
    consent = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"], notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    db.get(Consent, UUID(consent["id"])).expires_at = None
    request = db.scalar(select(RegistryRequest).where(RegistryRequest.case_id == case_id))
    request.status = "pending"
    request.attempt_count = 1
    request.updated_at = datetime.now(timezone.utc)
    db.add(RequestAttempt(registry_request_id=request.id, attempt_number=1, status="started"))
    db.commit()

    class SuccessfulConnector:
        calls = 0

        def query(self, organization, service, payload):
            self.calls += 1
            return {"status": "ok", "data": {"valid": True}, "transport_id": "recovered"}

    connector = SuccessfulConnector()
    monkeypatch.setattr(connectors, "build_connector", lambda: connector)

    first = execute_checks(case_id, agent, db)
    assert first["status"] == "pending"
    assert connector.calls == 0
    assert request.attempt_count == 1

    request.updated_at = datetime.now(timezone.utc) - timedelta(seconds=61)
    db.commit()
    recovered = execute_checks(case_id, agent, db)

    assert recovered["status"] == "completed"
    assert connector.calls == 1
    assert recovered["checks"][0]["attempt_count"] == 2
    attempts = db.scalars(
        select(RequestAttempt).where(RequestAttempt.registry_request_id == request.id).order_by(RequestAttempt.attempt_number)
    ).all()
    assert [attempt.status for attempt in attempts] == ["failed", "succeeded"]
    assert attempts[0].error_code == "attempt_lease_expired"
