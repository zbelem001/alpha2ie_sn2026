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
    CitizenIdentifiersUpdate,
    ConsentCreate,
    DocumentIdentifierInput,
    IdentityLinkCreate,
    CitizenCaseCreate,
    ConsultationReport,
    create_case,
    get_journal,
    report_consultation,
    start_citizen_case,
    execute_checks,
    link_citizen_identity,
    get_citizen_identifiers,
    list_notifications,
    mark_notification_read,
    record_consent,
    revoke_consent,
    save_citizen_identifiers,
    RegistrationOtpVerify,
    verify_registration_otp,
)
from app.database.base import Base
from app.database.models import (
    Administration,
    AuditEvent,
    Case,
    CitizenDocumentIdentifier,
    CitizenIdentityLink,
    Consent,
    Notification,
    Permission,
    Procedure,
    ProcedureQuestion,
    RegistrationOtpChallenge,
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
        active=True,
        published=True,
    )
    db.add(procedure)
    db.flush()
    db.add(ProcedureQuestion(procedure_id=procedure.id, question_id=question.id, required=True, position=1))
    db.add(Permission(
        requester_administration_id=owner.id, question_id=question.id,
        active=True, status="approved",
    ))
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


def test_case_create_accepts_frontend_camel_case_and_document_references(db: Session, monkeypatch):
    from cryptography.fernet import Fernet

    owner, _, procedure = add_procedure(db)
    subject_ref = "CITIZEN:FRONTEND-TEST"
    db.add(CitizenIdentityLink(
        principal_sub="citizen-sub", subject_ref=subject_ref, phone_number="+22670000001"
    ))
    db.commit()
    monkeypatch.setenv("CITIZEN_IDENTIFIER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    body = CaseCreate.model_validate({
        "procedureCode": procedure.code,
        "channel": "assisted",
        "phone": "70000001",
        "applicantName": "Awa Demo",
        "references": {"cnib": "CNIB-DEMO-123456"},
    })

    result = create_case(body, agent, db)

    assert result["applicantName"] == "Awa Demo"
    assert result["procedureCode"] == procedure.code
    assert result["channel"] == "assisted"
    assert result["phone"] == "+22670000001"
    assert result["checks"][0]["questionCode"] == "passport_cnib_valid"
    assert result["checks"][0]["document"]["key"] == "cnib"
    assert result["checks"][0]["attemptCount"] == 0


def test_simulated_registration_otp_is_accepted_for_demo_with_explicit_mode(db: Session, monkeypatch):
    from uuid import uuid4
    from app.otp_simulation import code_for, digest_code

    monkeypatch.setenv("OTP_SIMULATION_SECRET", "test-secret-value-at-least-thirty-two-characters")
    challenge_id = uuid4()
    challenge = RegistrationOtpChallenge(
        id=challenge_id,
        phone_number="+22670000001",
        provider_pin_id=None,
        code_digest=digest_code(challenge_id, "registration", code_for(challenge_id, "registration")),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        resend_after=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    db.add(challenge)
    db.commit()

    result = verify_registration_otp(
        RegistrationOtpVerify(challenge_id=challenge_id, code=code_for(challenge_id, "registration")), db
    )

    assert result["phone_verified"] is True
    assert result["phoneVerificationSimulated"] is True
    assert result["verification_mode"] == "simulation"
    assert result["otp_validated"] is True


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
    assert "Connectez-vous à la plateforme" in notifications[0].message
    assert "consentement" in notifications[1].message
    assert "{" not in notifications[1].message and "}" not in notifications[1].message
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


def test_case_creation_dispatches_infobip_for_configured_demo_citizen(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    monkeypatch.setenv("SMS_PROVIDER", "infobip")
    monkeypatch.setenv("INFOBIP_SMS_API_KEY", "test-api-key")
    monkeypatch.setenv("INFOBIP_BASE_URL", "test.api.infobip.com")
    monkeypatch.setenv("INFOBIP_SENDER", "DLNUF")
    monkeypatch.setenv("TEST_PHONE_NUMBER", "+22670000000")
    db.add(CitizenIdentityLink(
        principal_sub=citizen.subject,
        subject_ref=citizen.citizen_ref,
        phone_number="+22670000001",
    ))
    db.commit()
    sent = {}

    class FakeProvider:
        def send(self, body):
            sent.update(body=body)
            from app.sms_provider import SmsSendResult
            return SmsSendResult("infobip-test-message", "PENDING_ACCEPTED", "PENDING")

    monkeypatch.setattr("app.sms.build_sms_provider", FakeProvider)
    case = create_case(CaseCreate(procedure_code=procedure.code, subject_ref=citizen.citizen_ref), agent, db)
    sms = db.scalar(select(Notification).where(
        Notification.case_id == UUID(case["id"]), Notification.channel == "sms"
    ))

    assert sms.delivery_status == "sent"
    assert sms.provider_message_id == "infobip-test-message"
    assert sms.delivery_error is None
    assert "Répondez sur la plateforme" in sent["body"]
    assert procedure.title in sent["body"]
    assert case["id"][:8].upper() in sent["body"]


def identity_proof(**overrides):
    """Rattachement d'Awa avec sa preuve de titularité (nom de la mère inscrit sur l'acte)."""
    values = {
        "subject_ref": "ACTE:OUAGA:2004:01234", "confirmed": True, "last_name": "KABORE",
        "first_names": "Awa", "birth_date": "2004-03-12", "mother_name": "COMPAORE Salimata",
    }
    return IdentityLinkCreate.model_validate({**values, **overrides})


class MatchConnector:
    def __init__(self, reply):
        self.reply = reply

    def query(self, organization, service, payload):
        return self.reply


def test_identity_link_requires_the_holder_proof_without_revealing_why(db: Session, monkeypatch):
    citizen = Principal("proof-sub", frozenset({"citizen"}), None, None, phone_number="+22670000077", phone_number_verified=True)
    messages = []
    for reply in ({"status": "ok", "data": {"match": False}}, {"status": "not_found", "data": None}):
        monkeypatch.setattr(connectors, "build_connector", lambda reply=reply: MatchConnector(reply))
        with pytest.raises(HTTPException) as refused:
            link_citizen_identity(identity_proof(mother_name="KONATE Aminata"), citizen, db)
        assert refused.value.status_code == 422
        messages.append(refused.value.detail)
    # Même réponse pour un acte inexistant et pour une preuve fausse : rien n'est révélé.
    assert messages[0] == messages[1]
    assert db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == "proof-sub")) is None


def test_identity_link_conflict_is_reported_only_after_the_proof(db: Session, monkeypatch):
    db.add(CitizenIdentityLink(principal_sub="first-owner", subject_ref="ACTE:OUAGA:2004:01234", phone_number="+22670000001"))
    db.commit()
    intruder = Principal("intruder-sub", frozenset({"citizen"}), None, None, phone_number="+22670000088", phone_number_verified=True)
    monkeypatch.setattr(connectors, "build_connector", lambda: MatchConnector({"status": "ok", "data": {"match": False}}))
    with pytest.raises(HTTPException) as wrong_proof:
        link_citizen_identity(identity_proof(mother_name="Inconnue"), intruder, db)
    assert wrong_proof.value.status_code == 422
    monkeypatch.setattr(connectors, "build_connector", lambda: MatchConnector({"status": "ok", "data": {"match": True}}))
    with pytest.raises(HTTPException) as already_linked:
        link_citizen_identity(identity_proof(), intruder, db)
    assert already_linked.value.status_code == 409


def test_identity_link_attempts_are_limited(db: Session, monkeypatch):
    citizen = Principal("guesser-sub", frozenset({"citizen"}), None, None, phone_number="+22670000066", phone_number_verified=True)
    monkeypatch.setattr(connectors, "build_connector", lambda: MatchConnector({"status": "ok", "data": {"match": False}}))
    for _ in range(5):
        with pytest.raises(HTTPException) as refused:
            link_citizen_identity(identity_proof(mother_name="Essai"), citizen, db)
        assert refused.value.status_code == 422
    monkeypatch.setattr(connectors, "build_connector", lambda: MatchConnector({"status": "ok", "data": {"match": True}}))
    with pytest.raises(HTTPException) as blocked:
        link_citizen_identity(identity_proof(), citizen, db)
    assert blocked.value.status_code == 429


def test_citizen_can_link_confirmed_reference_with_verified_phone(db: Session, monkeypatch):
    citizen = Principal(
        "citizen-sub", frozenset({"citizen"}), None, None,
        phone_number="+22670000099", phone_number_verified=True,
    )

    class IdentityConnector:
        def query(self, organization, service, payload):
            assert organization == "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
            assert service == "identity-match"
            assert payload["subject"] == {
                "pivot_id": "ACTE:OUAGA:2004:01234", "last_name": "KABORE", "first_names": "Awa",
                "birth_date": "2004-03-12", "mother_name": "COMPAORE Salimata",
            }
            return {"status": "ok", "data": {"match": True}}

    monkeypatch.setattr(connectors, "build_connector", lambda: IdentityConnector())
    result = link_citizen_identity(identity_proof(subject_ref="acte:ouaga:2004:01234"), citizen, db)

    assert result == {"linked": True, "subject_ref": "ACTE:OUAGA:2004:01234"}
    stored = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == citizen.subject))
    assert stored.subject_ref == "ACTE:OUAGA:2004:01234"
    assert stored.phone_number == "+22670000099"


def test_citizen_identity_link_requires_confirmation_and_verified_phone(db: Session):
    unverified = Principal("citizen-sub", frozenset({"citizen"}), None, None, "+22670000099", False)
    with pytest.raises(HTTPException) as unchecked:
        link_citizen_identity(identity_proof(confirmed=False), unverified, db)
    assert unchecked.value.status_code == 422

    with pytest.raises(HTTPException) as no_verified_phone:
        link_citizen_identity(identity_proof(), unverified, db)
    assert no_verified_phone.value.status_code == 403


def test_citizen_can_register_optional_encrypted_document_identifiers(db: Session, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("CITIZEN_IDENTIFIER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, None, "+22670000099", False)
    body = CitizenIdentifiersUpdate(
        confirmed=True,
        identifiers=[DocumentIdentifierInput(identifier_type="cnib_number", value="cnib-demo-123456")],
    )

    result = save_citizen_identifiers(body, citizen, db)

    assert result["linked"] is True
    assert result["identifier_types"] == ["cnib_number"]
    stored = db.scalar(select(CitizenDocumentIdentifier).where(
        CitizenDocumentIdentifier.principal_sub == citizen.subject
    ))
    assert stored.identifier_ciphertext != "CNIB-DEMO-123456"
    assert get_citizen_identifiers(citizen, db)["identifiers"] == [
        {"identifier_type": "cnib_number", "value": "CNIB-DEMO-123456"}
    ]


def test_agent_can_find_citizen_by_document_identifier(db: Session, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("CITIZEN_IDENTIFIER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    owner, _, procedure = add_procedure(db)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, None, "+22670000099", False)
    save_citizen_identifiers(
        CitizenIdentifiersUpdate(
            confirmed=True,
            identifiers=[DocumentIdentifierInput(identifier_type="cnib_number", value="CNIB-DEMO-123456")],
        ),
        citizen,
        db,
    )
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)

    created = create_case(
        CaseCreate(
            procedure_code=procedure.code,
            citizen_identifier=DocumentIdentifierInput(identifier_type="cnib_number", value="cnib-demo-123456"),
        ),
        agent,
        db,
    )

    case = db.get(Case, UUID(created["id"]))
    request = db.scalar(select(RegistryRequest).where(RegistryRequest.case_id == case.id))
    assert case.subject_ref.startswith("CITIZEN:")
    assert request.lookup_identifier_type == "cnib_number"
    assert request.lookup_identifier_ciphertext != "CNIB-DEMO-123456"

    linked_citizen = Principal("citizen-sub", frozenset({"citizen"}), None, case.subject_ref)
    consent = record_consent(
        case.id,
        ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"], notice_version="demo-1", channel="web"),
        linked_citizen,
        db,
    )
    db.get(Consent, UUID(consent["id"])).expires_at = None

    class RegistryConnector:
        def query(self, organization, service, payload):
            assert payload["subject"] == {}
            assert payload["parameters"] == {
                "identifier_type": "cnib_number",
                "document_identifier": "CNIB-DEMO-123456",
            }
            return {"status": "ok", "data": {"valid": True}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: RegistryConnector())
    result = execute_checks(UUID(created["id"]), agent, db)
    assert result["status"] == "completed"
    assert request.lookup_identifier_ciphertext is None


def test_document_reference_is_sent_with_the_expected_holder(db: Session, monkeypatch):
    """Avec une référence de pièce, le registre reçoit aussi le titulaire attendu, pour vérifier la concordance."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("CITIZEN_IDENTIFIER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    owner, _, procedure = add_procedure(db)
    subject_ref = "ACTE:OUAGA:2004:01234"
    db.add(CitizenIdentityLink(principal_sub="citizen-sub", subject_ref=subject_ref, phone_number="+22670000001"))
    db.commit()
    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    created = create_case(CaseCreate.model_validate({
        "procedureCode": procedure.code, "channel": "web", "phone": "70000001",
        "references": {"cnib": "CNIB-DEMO-123456"},
    }), agent, db)
    case_id = UUID(created["id"])
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, subject_ref)
    consent = record_consent(
        case_id,
        ConsentCreate(decision="granted", question_codes=["passport_cnib_valid"], notice_version="demo-1", channel="web"),
        citizen,
        db,
    )
    db.get(Consent, UUID(consent["id"])).expires_at = None

    class RegistryConnector:
        def query(self, organization, service, payload):
            assert payload["subject"] == {"pivot_id": subject_ref}
            assert payload["parameters"] == {"identifier_type": "cnib_number", "document_identifier": "CNIB-DEMO-123456"}
            return {"status": "ok", "data": {"valid": True}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: RegistryConnector())
    assert execute_checks(case_id, agent, db)["status"] == "completed"


def test_citizen_can_start_a_procedure_without_an_agent(db: Session, monkeypatch):
    """Démarche lancée depuis l'espace usager : accord enregistré, vérifications aussitôt, sans guichet."""
    owner, _, procedure = add_procedure(db)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234", display_name="Awa KABORE")

    class SuccessfulConnector:
        def query(self, organization, service, payload):
            assert payload["subject"] == {"pivot_id": "ACTE:OUAGA:2004:01234"}
            return {"status": "ok", "data": {"valid": True}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: SuccessfulConnector())
    result = start_citizen_case(CitizenCaseCreate(procedure_code=procedure.code, confirmed=True), citizen, db)

    assert result["status"] == "completed"
    assert result["checks"][0]["status"] == "confirmed"
    case = db.get(Case, UUID(result["id"]))
    assert case.requester_administration_id == owner.id and case.consent_channel == "web"
    events = db.scalars(select(AuditEvent).where(AuditEvent.case_id == case.id).order_by(AuditEvent.occurred_at)).all()
    assert [event.event_type for event in events][:2] == ["case_created", "consent_recorded"]
    assert events[0].actor_type == "citizen"
    assert any(event.event_type == "registry_check" and event.outcome == "confirmed" for event in events)


def test_citizen_start_requires_link_confirmation_and_published_procedure(db: Session):
    add_procedure(db)
    linked = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")
    unlinked = Principal("other-sub", frozenset({"citizen"}), None, None)
    cases = [
        (CitizenCaseCreate(procedure_code="passeport_ordinaire_precheck", confirmed=False), linked, 422),
        (CitizenCaseCreate(procedure_code="passeport_ordinaire_precheck", confirmed=True), unlinked, 403),
        (CitizenCaseCreate(procedure_code="demarche_inconnue", confirmed=True), linked, 404),
    ]
    for body, principal, expected in cases:
        with pytest.raises(HTTPException) as refused:
            start_citizen_case(body, principal, db)
        assert refused.value.status_code == expected
    assert db.scalar(select(func.count()).select_from(Case)) == 0


def test_citizen_reports_a_consultation_once_and_the_requester_sees_it(db: Session, monkeypatch):
    owner, _, procedure = add_procedure(db)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")

    class SuccessfulConnector:
        def query(self, organization, service, payload):
            return {"status": "ok", "data": {"valid": True}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: SuccessfulConnector())
    case_id = UUID(start_citizen_case(CitizenCaseCreate(procedure_code=procedure.code, confirmed=True), citizen, db)["id"])
    consultation = db.scalar(select(AuditEvent).where(AuditEvent.case_id == case_id, AuditEvent.event_type == "registry_check"))

    report = report_consultation(case_id, consultation.id, ConsultationReport(reason="not_me"), citizen, db)
    assert report["status"] == "open" and report["event_id"] == str(consultation.id)
    with pytest.raises(HTTPException) as again:
        report_consultation(case_id, consultation.id, ConsultationReport(reason="not_me"), citizen, db)
    assert again.value.status_code == 409
    report_consultation(case_id, consultation.id, ConsultationReport(reason="wrong_result"), citizen, db)

    agent = Principal("agent-sub", frozenset({"agent"}), owner.code, None)
    journal = get_journal(case_id, agent, db)
    reports = {event["event_type"]: event for event in journal if event["event_type"] in {"consultation_contested", "correction_requested"}}
    assert set(reports) == {"consultation_contested", "correction_requested"}
    assert all(event["correlation_id"] == str(consultation.id) and event["outcome"] == "open" for event in reports.values())


def test_only_the_citizen_can_report_and_only_a_registry_consultation(db: Session, monkeypatch):
    _, _, procedure = add_procedure(db)
    citizen = Principal("citizen-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:2004:01234")

    class SuccessfulConnector:
        def query(self, organization, service, payload):
            return {"status": "ok", "data": {"valid": True}, "transport_id": "test-transport"}

    monkeypatch.setattr(connectors, "build_connector", lambda: SuccessfulConnector())
    case_id = UUID(start_citizen_case(CitizenCaseCreate(procedure_code=procedure.code, confirmed=True), citizen, db)["id"])
    created = db.scalar(select(AuditEvent).where(AuditEvent.case_id == case_id, AuditEvent.event_type == "case_created"))
    consultation = db.scalar(select(AuditEvent).where(AuditEvent.case_id == case_id, AuditEvent.event_type == "registry_check"))
    with pytest.raises(HTTPException) as not_a_consultation:
        report_consultation(case_id, created.id, ConsultationReport(reason="not_me"), citizen, db)
    assert not_a_consultation.value.status_code == 422
    someone_else = Principal("other-sub", frozenset({"citizen"}), None, "ACTE:OUAGA:1998:00456")
    with pytest.raises(HTTPException) as forbidden:
        report_consultation(case_id, consultation.id, ConsultationReport(reason="not_me"), someone_else, db)
    assert forbidden.value.status_code == 403
    with pytest.raises(ValidationError):
        ConsultationReport(reason="autre")


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
