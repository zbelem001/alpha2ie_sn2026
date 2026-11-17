from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import connectors
from app.api import CaseCreate, ConsentCreate, create_case, execute_checks, record_consent
from app.database.base import Base
from app.database.models import (
    Administration,
    Case,
    Consent,
    Permission,
    Procedure,
    ProcedureQuestion,
    Question,
    Registry,
    RegistryRequest,
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
