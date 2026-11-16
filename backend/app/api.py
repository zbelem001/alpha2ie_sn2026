"""Routes métier MVP, protégées par des jetons Bearer Keycloak."""
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Administration,
    AuditEvent,
    Case,
    Consent,
    ConsentQuestion,
    Permission,
    Procedure,
    ProcedureQuestion,
    Question,
    Registry,
    RegistryRequest,
    RequestAttempt,
)
from app.security import Principal, get_current_principal, require_role

router = APIRouter(prefix="/v1")


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    procedure_code: str
    subject_ref: str = Field(min_length=1, max_length=160)


class ConsentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(granted|refused)$")
    question_codes: list[str] = Field(min_length=1)
    notice_version: str
    channel: str = Field(pattern="^(in_person|sms|web|assisted)$")
    expires_at: datetime | None = None


def _add_event(
    db: Session,
    case: Case,
    event_type: str,
    purpose: str,
    *,
    outcome: str | None = None,
    actor_type: str = "system",
    actor_ref: str | None = None,
    question: Question | None = None,
    registry: Registry | None = None,
    categories: list[str] | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    previous = db.scalar(
        select(AuditEvent).where(AuditEvent.case_id == case.id).order_by(AuditEvent.occurred_at.desc())
    )
    occurred_at = datetime.now(timezone.utc)
    fields = {
        "case_id": str(case.id),
        "event_type": event_type,
        "outcome": outcome,
        "occurred_at": occurred_at.isoformat(),
        "previous_hash": previous.event_hash if previous else None,
    }
    event_hash = hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()
    event = AuditEvent(
        case_id=case.id,
        subject_ref=case.subject_ref,
        actor_type=actor_type,
        actor_ref=actor_ref,
        requester_administration_id=case.requester_administration_id,
        registry_id=registry.id if registry else None,
        question_id=question.id if question else None,
        event_type=event_type,
        outcome=outcome,
        purpose=purpose,
        data_categories=categories,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
        previous_hash=previous.event_hash if previous else None,
        event_hash=event_hash,
    )
    db.add(event)
    return event


def _check_payload(db: Session, request: RegistryRequest) -> dict:
    question = db.get(Question, request.question_id)
    registry = db.get(Registry, question.registry_id)
    administration = db.get(Administration, registry.administration_id)
    return {
        "question": question,
        "registry": registry,
        "payload": {
            "request_id": str(request.id),
            "procedure": db.get(Procedure, db.get(Case, request.case_id).procedure_id).code,
            "subject": {"pivot_id": db.get(Case, request.case_id).subject_ref},
        },
        "organization": administration.code,
    }


def _serialize_check(db: Session, request: RegistryRequest) -> dict:
    question = db.get(Question, request.question_id)
    return {
        "question_code": question.code,
        "status": request.status,
        "result": request.minimal_result,
        "message": None,
        "attempt_count": request.attempt_count,
    }


def _serialize_case(db: Session, case: Case) -> dict:
    procedure = db.get(Procedure, case.procedure_id)
    checks = db.scalars(select(RegistryRequest).where(RegistryRequest.case_id == case.id)).all()
    return {
        "id": str(case.id),
        "procedure_code": procedure.code,
        "subject_ref": case.subject_ref,
        "status": case.status,
        "checks": [_serialize_check(db, item) for item in checks],
        "created_at": case.created_at,
    }


def _case_or_404(db: Session, case_id: UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return case


def _authorize_case_access(case: Case, db: Session, principal: Principal) -> None:
    if "agent" in principal.roles:
        administration = db.get(Administration, case.requester_administration_id)
        if administration and principal.administration_code == administration.code:
            return
    if "citizen" in principal.roles and principal.citizen_ref == case.subject_ref:
        return
    raise HTTPException(status_code=403, detail="Accès interdit à ce dossier")


@router.get("/procedures")
def list_procedures(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    procedures = db.scalars(select(Procedure).where(Procedure.active.is_(True))).all()
    result = []
    for procedure in procedures:
        links = db.scalars(
            select(ProcedureQuestion)
            .where(ProcedureQuestion.procedure_id == procedure.id)
            .order_by(ProcedureQuestion.position)
        ).all()
        result.append({
            "code": procedure.code,
            "title": procedure.title,
            "questions": [
                {"code": (question := db.get(Question, link.question_id)).code,
                 "description": question.description, "required": link.required}
                for link in links
            ],
        })
    return result


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreate,
    principal: Principal = Depends(require_role("agent")),
    db: Session = Depends(get_db),
):
    procedure = db.scalar(select(Procedure).where(Procedure.code == body.procedure_code, Procedure.active.is_(True)))
    if not principal.administration_code:
        raise HTTPException(status_code=403, detail="Jeton agent sans administration")
    requester = db.scalar(select(Administration).where(Administration.code == principal.administration_code,
                                                       Administration.active.is_(True)))
    if procedure is None or requester is None:
        raise HTTPException(status_code=404, detail="Démarche ou administration inconnue")
    links = db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id)).all()
    if not links:
        raise HTTPException(status_code=409, detail="La démarche ne contient aucune vérification")
    case = Case(procedure_id=procedure.id, requester_administration_id=requester.id,
                subject_ref=body.subject_ref, status="received")
    db.add(case)
    db.flush()
    for link in links:
        question = db.get(Question, link.question_id)
        db.add(RegistryRequest(case_id=case.id, question_id=question.id, status="queued",
                               idempotency_key=f"{case.id}:{question.code}"))
    _add_event(db, case, "case_created", procedure.code, outcome="received", actor_type="agent",
               actor_ref=requester.code)
    db.commit()
    db.refresh(case)
    return _serialize_case(db, case)


@router.get("/cases/{case_id}")
def get_case(
    case_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    return _serialize_case(db, case)


@router.post("/cases/{case_id}/consent", status_code=status.HTTP_201_CREATED)
def record_consent(
    case_id: UUID,
    body: ConsentCreate,
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    if principal.citizen_ref != case.subject_ref:
        raise HTTPException(status_code=403, detail="Seul le citoyen concerné peut répondre au consentement")
    links = db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == case.procedure_id)).all()
    allowed = {db.get(Question, link.question_id).code: link.question_id for link in links}
    if len(set(body.question_codes)) != len(body.question_codes) or not set(body.question_codes) <= allowed.keys():
        raise HTTPException(status_code=422, detail="Une ou plusieurs questions ne font pas partie de la démarche")
    now = datetime.now(timezone.utc)
    consent = Consent(case_id=case.id, subject_ref=case.subject_ref, status=body.decision,
                      granted_at=now if body.decision == "granted" else None,
                      expires_at=body.expires_at, notice_version=body.notice_version, channel=body.channel)
    db.add(consent)
    db.flush()
    for code in body.question_codes:
        db.add(ConsentQuestion(consent_id=consent.id, question_id=allowed[code]))
    _add_event(db, case, "consent_recorded", "consentement pour la démarche",
               outcome=body.decision, actor_type="citizen", actor_ref=case.subject_ref)
    db.commit()
    db.refresh(consent)
    return {"id": str(consent.id), "case_id": str(case.id), "status": consent.status,
            "question_codes": body.question_codes, "notice_version": consent.notice_version,
            "channel": consent.channel, "granted_at": consent.granted_at,
            "revoked_at": consent.revoked_at, "expires_at": consent.expires_at}


@router.delete("/cases/{case_id}/consent")
def revoke_consent(
    case_id: UUID,
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    if principal.citizen_ref != case.subject_ref:
        raise HTTPException(status_code=403, detail="Seul le citoyen concerné peut révoquer son consentement")
    consent = db.scalar(select(Consent).where(Consent.case_id == case.id, Consent.status == "granted")
                        .order_by(Consent.created_at.desc()))
    if consent is None:
        raise HTTPException(status_code=404, detail="Aucun consentement actif")
    consent.status = "revoked"
    consent.revoked_at = datetime.now(timezone.utc)
    _add_event(db, case, "consent_revoked", "retrait du consentement", outcome="revoked",
               actor_type="citizen", actor_ref=case.subject_ref)
    db.commit()
    return {"id": str(consent.id), "case_id": str(case.id), "status": consent.status,
            "revoked_at": consent.revoked_at}


@router.post("/cases/{case_id}/checks")
def execute_checks(
    case_id: UUID,
    principal: Principal = Depends(require_role("agent")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    now = datetime.now(timezone.utc)
    consent = db.scalar(select(Consent).where(Consent.case_id == case.id, Consent.status == "granted")
                        .order_by(Consent.created_at.desc()))
    requests = db.scalars(select(RegistryRequest).where(RegistryRequest.case_id == case.id)).all()
    links = {link.question_id: link for link in db.scalars(
        select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == case.procedure_id)).all()}
    consent_ids = set()
    if consent and (consent.expires_at is None or consent.expires_at > now):
        consent_ids = set(db.scalars(select(ConsentQuestion.question_id).where(ConsentQuestion.consent_id == consent.id)).all())
    if consent is None or not consent_ids:
        for request in requests:
            request.status = "blocked"
        _add_event(db, case, "checks_blocked", "consentement absent ou expiré", outcome="blocked")
        case.status = "pending"
        db.commit()
        raise HTTPException(status_code=403, detail="Consentement citoyen actif requis")

    from connectors import build_connector

    connector = build_connector()
    for request in requests:
        if request.status in {"confirmed", "rejected", "not_found", "ambiguous", "blocked"}:
            continue
        question = db.get(Question, request.question_id)
        link = links[question.id]
        permission = db.scalar(select(Permission).where(
            Permission.requester_administration_id == case.requester_administration_id,
            Permission.question_id == question.id,
            Permission.active.is_(True),
            (Permission.valid_from.is_(None) | (Permission.valid_from <= now)),
            (Permission.valid_until.is_(None) | (Permission.valid_until > now)),
        ))
        if not question.active or permission is None or question.id not in consent_ids:
            request.status = "blocked"
            _add_event(db, case, "check_blocked", "consentement ou autorisation absent", outcome="blocked", question=question)
            continue
        registry_info = _check_payload(db, request)
        request.attempt_count += 1
        attempt = RequestAttempt(registry_request_id=request.id, attempt_number=request.attempt_count, status="started")
        db.add(attempt)
        request.status = "pending"
        db.commit()
        try:
            reply = connector.query(registry_info["organization"], question.service_code, registry_info["payload"])
        except Exception:
            reply = {"status": "unavailable", "data": None, "message": "Registre indisponible", "transport_id": None}
        transport_status = reply.get("status")
        data = reply.get("data") if transport_status == "ok" else None
        value = data.get(question.response_key) if isinstance(data, dict) else None
        if transport_status == "ok" and value is not None:
            request.status = "confirmed" if value is True else "rejected" if value is False else "confirmed"
            request.minimal_result = {question.response_key: value}
            attempt.status = "succeeded"
        else:
            mapping = {"not_found": "not_found", "ambiguous": "ambiguous", "refused": "blocked",
                       "unavailable": "unavailable", "invalid_request": "error"}
            request.status = mapping.get(transport_status, "error")
            request.minimal_result = None
            attempt.status = "failed"
            attempt.error_code = transport_status or "invalid_response"
        attempt.finished_at = datetime.now(timezone.utc)
        attempt.transport_id = reply.get("transport_id")
        _add_event(db, case, "registry_check", question.description, outcome=request.status,
                   actor_type="administration", question=question, registry=registry_info["registry"],
                   categories=[question.code], correlation_id=str(request.id))
        db.commit()

    required_states = [request.status for request in requests if links[request.question_id].required]
    if any(state == "rejected" for state in required_states):
        case.status = "rejected"
    elif any(state in {"queued", "pending", "unavailable", "blocked", "error", "ambiguous", "not_found"}
             for state in required_states):
        case.status = "pending"
    elif required_states and all(state == "confirmed" for state in required_states):
        case.status = "completed"
    else:
        case.status = "in_progress"
    case.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"case_id": str(case.id), "status": case.status,
            "checks": [_serialize_check(db, item) for item in requests]}


@router.get("/cases/{case_id}/journal")
def get_journal(
    case_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    events = db.scalars(select(AuditEvent).where(AuditEvent.case_id == case.id)
                        .order_by(AuditEvent.occurred_at)).all()
    return [{"id": str(event.id), "occurred_at": event.occurred_at,
             "event_type": event.event_type, "requester": db.get(Administration, event.requester_administration_id).name
             if event.requester_administration_id else None,
             "registry": db.get(Registry, event.registry_id).code if event.registry_id else None,
             "question_code": db.get(Question, event.question_id).code if event.question_id else None,
             "purpose": event.purpose, "outcome": event.outcome,
             "data_categories": event.data_categories} for event in events]
