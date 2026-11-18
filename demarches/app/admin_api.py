"""Administration-scoped management API for the local administration console."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from connectors.administrations import load_administrations

from app.database.connection import get_db
from app.journal import JournalUnavailable, journal
from app.database.models import (
    Administration,
    AdministrationAuditEvent,
    Case,
    Permission,
    Procedure,
    ProcedureQuestion,
    Question,
    Registry,
    RegistryService,
)
from app.keycloak_admin import KeycloakAdminClient
from app.security import Principal, require_role
from app.xroad_sync import XRoadSync, XRoadSyncError

router = APIRouter(prefix="/v1/admin", tags=["administration"])

QUESTION_DOCUMENT_KEYS = {
    "candidate_minimum_age": "birth",
    "candidate_nationality": "nationality",
    "criminal_record_indicator": "criminal",
    "passport_cnib_valid": "cnib",
    "passport_birth_act_found": "birth",
    "passport_nationality": "nationality",
    "passport_criminal_record_current": "criminal",
    "passport_fiscal_stamp_paid": "payment",
    "loss_declared": "loss",
}
DOCUMENT_IDENTIFIERS = {
    "cnib": "cnib_number",
    "birth": "birth_act_number",
    "nationality": "nationality_reference",
    "criminal": "criminal_record_number",
    "payment": "payment_reference",
    "loss": "loss_report_number",
}


class DocumentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    key: str = Field(pattern="^(cnib|birth|nationality|criminal|payment|loss)$")
    label: str = Field(min_length=2, max_length=160)
    provider: str = Field(min_length=2, max_length=120)
    hint: str = Field(max_length=300)


class ProcedureCheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    question_code: str = Field(min_length=2, max_length=100, validation_alias=AliasChoices("question_code", "questionCode"))
    required: bool = True
    document: DocumentConfig


class ProcedureInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)
    code: str = Field(min_length=3, max_length=64, pattern="^[a-z][a-z0-9_]{2,63}$")
    title: str = Field(min_length=3, max_length=200)
    purpose: str = Field(min_length=5, max_length=2000)
    consent_days: int = Field(ge=1, le=30, validation_alias=AliasChoices("consent_days", "consentDays"))
    published: bool = False
    checks: list[ProcedureCheckInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_checks(self):
        codes = [check.question_code for check in self.checks]
        if len(codes) != len(set(codes)):
            raise ValueError("Une vérification ne peut apparaître qu’une fois")
        if not any(check.required for check in self.checks):
            raise ValueError("Au moins une vérification doit être obligatoire")
        for check in self.checks:
            expected = QUESTION_DOCUMENT_KEYS.get(check.question_code)
            if expected is not None and expected != check.document.key:
                raise ValueError("Le type de document ne correspond pas à la vérification sélectionnée")
        return self


class RightRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    purpose: str = Field(min_length=5, max_length=1000)


class RegistryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=3, max_length=200)
    url: str = Field(min_length=8, max_length=500)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parts = urlsplit(value.strip())
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Utilisez une URL HTTP(S) valide sans identifiants")
        if parts.query or parts.fragment:
            raise ValueError("L’URL du registre ne doit pas contenir de paramètres ni de fragment")
        return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


class ServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=3, max_length=64, pattern="^[a-z][a-z0-9-]{2,63}$")
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=1000)
    response_key: str = Field(default="valid", min_length=1, max_length=100,
                              pattern="^[a-z][a-z0-9_]*$", validation_alias=AliasChoices("response_key", "responseKey"))


class ActiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool


class AgentCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=8, max_length=24)
    pin: str = Field(pattern="^[0-9]{6}$")


class PinResetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pin: str = Field(pattern="^[0-9]{6}$")


def _administration(db: Session, principal: Principal) -> Administration:
    if not principal.administration_code:
        raise HTTPException(status_code=403, detail="Le jeton administrateur n’est associé à aucune administration")
    administration = db.scalar(select(Administration).where(
        Administration.code == principal.administration_code,
        Administration.code.in_(list(load_administrations())),
        Administration.active.is_(True),
    ))
    if administration is None:
        raise HTTPException(status_code=403, detail="Administration inconnue ou inactive")
    return administration


def _audit(
    db: Session,
    administration: Administration,
    principal: Principal,
    action: str,
    target: str,
    detail: str = "",
) -> None:
    db.add(AdministrationAuditEvent(
        administration_id=administration.id,
        actor_sub=principal.subject,
        actor_name=principal.display_name or principal.subject,
        actor_role="local-admin",
        action=action,
        target=target,
        detail=detail[:500],
    ))


def _primary_registry(db: Session, administration: Administration, *, create: bool = False) -> Registry | None:
    registry = db.scalar(select(Registry).where(
        Registry.administration_id == administration.id,
        Registry.code == "main",
    ))
    if registry is None and create:
        registry = Registry(
            administration_id=administration.id,
            code="main",
            name=f"Registre — {administration.name}",
            active=True,
        )
        db.add(registry)
        db.flush()
    return registry


def _procedure_payload(db: Session, procedure: Procedure) -> dict:
    links = db.scalars(select(ProcedureQuestion)
        .where(ProcedureQuestion.procedure_id == procedure.id)
        .order_by(ProcedureQuestion.position)).all()
    return {
        "code": procedure.code,
        "title": procedure.title,
        "purpose": procedure.purpose,
        "version": procedure.config_version,
        "consentDays": procedure.consent_days,
        "consent_days": procedure.consent_days,
        "active": procedure.active,
        "published": procedure.published,
        "checks": [
            {
                "question_code": (question := db.get(Question, link.question_id)).code,
                "questionCode": question.code,
                "required": link.required,
                "document": {
                    "key": link.document_type or QUESTION_DOCUMENT_KEYS.get(question.code, ""),
                    "label": link.document_label or question.description,
                    "provider": db.get(Administration, db.get(Registry, question.registry_id).administration_id).name,
                    "hint": link.document_hint or "",
                },
            }
            for link in links
        ],
    }


def _question_provider(db: Session, question: Question) -> str:
    registry = db.get(Registry, question.registry_id)
    owner = db.get(Administration, registry.administration_id) if registry else None
    return owner.name if owner else ""


def _question_provider_code(db: Session, question: Question) -> str | None:
    registry = db.get(Registry, question.registry_id)
    owner = db.get(Administration, registry.administration_id) if registry else None
    return owner.code if owner else None


def _registry_payload(registry: Registry | None) -> dict:
    if registry is None:
        return {"name": "", "url": "", "last_test": None, "lastTest": None}
    last_test = ({"at": registry.last_test_at, "success": registry.last_test_success}
                 if registry.last_test_at else None)
    return {
        "name": registry.name,
        "url": registry.base_url or "",
        "last_test": last_test,
        "lastTest": last_test,
    }


def _agent_payload(agent: dict) -> dict:
    payload = dict(agent)
    if "created_at" in payload:
        payload.setdefault("createdAt", payload["created_at"])
    return payload


def _rights(db: Session, administration_id: UUID) -> list[dict]:
    questions = db.scalars(select(Question).where(Question.active.is_(True)).order_by(Question.code)).all()
    result = []
    for question in questions:
        permission = db.scalar(select(Permission).where(
            Permission.requester_administration_id == administration_id,
            Permission.question_id == question.id,
        ))
        state = permission.status if permission else "not_requested"
        if permission and permission.active:
            state = "approved"
        result.append({
            "question_code": question.code,
            "questionCode": question.code,
            "label": question.description,
            "service_code": question.service_code,
            "provider": _question_provider(db, question),
            "status": state,
            "purpose": permission.purpose if permission else None,
            "requested_at": permission.requested_at if permission else None,
            "requestedAt": permission.requested_at if permission else None,
        })
    return result


def _ensure_publishable(db: Session, administration_id: UUID, checks: list[ProcedureCheckInput]) -> None:
    for check in checks:
        question = db.scalar(select(Question).where(Question.code == check.question_code, Question.active.is_(True)))
        if question is None:
            raise HTTPException(status_code=422, detail=f"Vérification inconnue ou inactive : {check.question_code}")
        permission = db.scalar(select(Permission).where(
            Permission.requester_administration_id == administration_id,
            Permission.question_id == question.id,
            Permission.active.is_(True),
            Permission.status == "approved",
        ))
        if permission is None:
            raise HTTPException(status_code=409, detail="Publication impossible : un droit d’échange n’est pas validé")


@router.get("/config")
def get_configuration(
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    procedures = db.scalars(select(Procedure).where(
        Procedure.owner_administration_id == administration.id,
    ).order_by(Procedure.title)).all()
    registry = _primary_registry(db, administration)
    services = db.scalars(select(RegistryService).where(
        RegistryService.registry_id == registry.id,
    ).order_by(RegistryService.title)).all() if registry else []
    available_services = db.execute(
        select(RegistryService, Administration)
        .join(Registry, RegistryService.registry_id == Registry.id)
        .join(Administration, Registry.administration_id == Administration.id)
        .where(RegistryService.active.is_(True), Registry.active.is_(True),
               Administration.code.in_(list(load_administrations())),
               Administration.active.is_(True), Administration.id != administration.id)
        .order_by(Administration.name, RegistryService.title)
    ).all()
    try:
        agents = [_agent_payload(item) for item in KeycloakAdminClient().list_agents(administration.code)]
        agent_management_available = True
    except HTTPException as error:
        if error.status_code not in {502, 503}:
            raise
        agents = []
        agent_management_available = False
    return {
        "administration": {"code": administration.code, "name": administration.name},
        "availableServices": [{
            "id": str(service.id), "code": service.code, "title": service.title,
            "description": service.description, "provider": provider.name,
            "providerCode": provider.code,
        } for service, provider in available_services],
        "procedures": [_procedure_payload(db, item) for item in procedures],
        "agents": agents,
        "agent_management_available": agent_management_available,
        "agentManagementAvailable": agent_management_available,
        "rights": _rights(db, administration.id),
        "registry": _registry_payload(registry),
        "offered_services": [{
            "id": str(service.id), "code": service.code, "title": service.title,
            "description": service.description, "active": service.active,
        } for service in services],
        "offeredServices": [{
            "id": str(service.id), "code": service.code, "title": service.title,
            "description": service.description, "active": service.active,
        } for service in services],
    }


@router.put("/procedures/{code}")
def save_procedure(
    code: str,
    body: ProcedureInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    if code != body.code:
        raise HTTPException(status_code=422, detail="Le code de la démarche ne peut pas être modifié")
    administration = _administration(db, principal)
    procedure = db.scalar(select(Procedure).where(Procedure.code == code))
    if procedure and procedure.owner_administration_id != administration.id:
        raise HTTPException(status_code=409, detail="Ce code de démarche appartient à une autre administration")
    if procedure:
        has_cases = db.scalar(select(func.count(Case.id)).where(Case.procedure_id == procedure.id)) or 0
        if has_cases:
            raise HTTPException(status_code=409, detail="Cette démarche a déjà des dossiers. Créez une nouvelle démarche pour préserver leur périmètre historique.")
    was_published = procedure.published if procedure else False
    was_active = procedure.active if procedure else False
    questions = {}
    for item in body.checks:
        question = db.scalar(select(Question).where(Question.code == item.question_code, Question.active.is_(True)))
        if question is None:
            raise HTTPException(status_code=422, detail=f"Vérification inconnue ou inactive : {item.question_code}")
        questions[item.question_code] = question
    if body.published:
        for item in body.checks:
            question = questions[item.question_code]
            permission = db.scalar(select(Permission).where(
                Permission.requester_administration_id == administration.id,
                Permission.question_id == question.id,
            ))
            if permission is None:
                permission = Permission(
                    requester_administration_id=administration.id,
                    question_id=question.id,
                    active=True,
                )
                db.add(permission)
            permission.status = "approved"
            permission.active = True
            permission.purpose = body.purpose
            permission.valid_from = datetime.now(timezone.utc)
        db.flush()
        _ensure_publishable(db, administration.id, body.checks)
    if procedure is None:
        procedure = Procedure(
            code=code,
            owner_administration_id=administration.id,
            title=body.title,
            purpose=body.purpose,
            consent_days=body.consent_days,
            published=body.published,
            active=body.published,
            config_version=1,
        )
        db.add(procedure)
        db.flush()
    else:
        procedure.title = body.title
        procedure.purpose = body.purpose
        procedure.consent_days = body.consent_days
        procedure.published = body.published
        procedure.active = body.published and (was_active if was_published else True)
        procedure.config_version += 1
        for link in db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id)).all():
            db.delete(link)
        db.flush()
    for position, item in enumerate(body.checks):
        document = item.document
        db.add(ProcedureQuestion(
            procedure_id=procedure.id,
            question_id=questions[item.question_code].id,
            required=item.required,
            position=position,
            document_type=document.key,
            document_label=document.label,
            document_hint=document.hint,
        ))
    if body.published:
        try:
            sync = XRoadSync()
            for item in body.checks:
                question = questions[item.question_code]
                provider_code = _question_provider_code(db, question)
                if provider_code:
                    sync.grant_access(administration.code, provider_code, question.service_code)
        except XRoadSyncError as error:
            raise HTTPException(status_code=503, detail=f"Synchronisation X-Road impossible : {error}") from error
        except httpx.HTTPError as error:
            raise HTTPException(status_code=503, detail="Le Security Server X-Road est indisponible") from error
    _audit(db, administration, principal,
           "Démarche publiée" if body.published else "Brouillon de démarche enregistré",
           body.title, f"Version {procedure.config_version}")
    db.commit()
    db.refresh(procedure)
    return _procedure_payload(db, procedure)


@router.patch("/procedures/{code}/active")
def set_procedure_active(
    code: str,
    body: ActiveInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    procedure = db.scalar(select(Procedure).where(
        Procedure.code == code,
        Procedure.owner_administration_id == administration.id,
    ))
    if procedure is None:
        raise HTTPException(status_code=404, detail="Démarche introuvable")
    if body.active:
        links = db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id)).all()
        if not procedure.published or not links:
            raise HTTPException(status_code=409, detail="Publiez la démarche et configurez ses vérifications avant de l’activer")
        checks = []
        for link in links:
            question = db.get(Question, link.question_id)
            if question:
                checks.append(ProcedureCheckInput(
                    question_code=question.code,
                    required=link.required,
                    document={"key": link.document_type or QUESTION_DOCUMENT_KEYS.get(question.code, ""),
                              "label": link.document_label or question.description,
                              "provider": _question_provider(db, question),
                              "hint": link.document_hint or ""},
                ))
        _ensure_publishable(db, administration.id, checks)
        try:
            sync = XRoadSync()
            for link in links:
                question = db.get(Question, link.question_id)
                if question:
                    provider_code = _question_provider_code(db, question)
                    if provider_code:
                        sync.grant_access(administration.code, provider_code, question.service_code)
        except (XRoadSyncError, httpx.HTTPError) as error:
            raise HTTPException(status_code=503, detail=f"Synchronisation X-Road impossible : {error}") from error
    else:
        links = db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id)).all()
        try:
            sync = XRoadSync()
            for link in links:
                question = db.get(Question, link.question_id)
                if question:
                    provider_code = _question_provider_code(db, question)
                    if provider_code:
                        sync.revoke_access(administration.code, provider_code, question.service_code)
        except (XRoadSyncError, httpx.HTTPError) as error:
            raise HTTPException(status_code=503, detail=f"Synchronisation X-Road impossible : {error}") from error
    procedure.active = body.active
    _audit(db, administration, principal,
           "Démarche activée" if body.active else "Démarche désactivée",
           procedure.title)
    db.commit()
    return {"code": procedure.code, "active": procedure.active, "published": procedure.published}


@router.post("/rights/{question_code}/request")
def request_right(
    question_code: str,
    body: RightRequestInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    question = db.scalar(select(Question).where(Question.code == question_code, Question.active.is_(True)))
    if question is None:
        raise HTTPException(status_code=404, detail="Information de registre introuvable")
    permission = db.scalar(select(Permission).where(
        Permission.requester_administration_id == administration.id,
        Permission.question_id == question.id,
    ))
    if permission and permission.status in {"approved", "requested"}:
        raise HTTPException(status_code=409, detail="Ce droit est déjà validé ou en attente")
    if permission is None:
        permission = Permission(
            requester_administration_id=administration.id,
            question_id=question.id,
            active=False,
        )
        db.add(permission)
    permission.status = "requested"
    permission.active = False
    permission.purpose = body.purpose
    permission.requested_at = datetime.now(timezone.utc)
    _audit(db, administration, principal, "Droit d’échange demandé", question.description, body.purpose)
    db.commit()
    return {"question_code": question.code, "status": permission.status, "purpose": permission.purpose,
            "requested_at": permission.requested_at}


@router.post("/rights/{question_code}/suspend")
def suspend_right(
    question_code: str,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    question = db.scalar(select(Question).where(Question.code == question_code))
    if question is None:
        raise HTTPException(status_code=404, detail="Information de registre introuvable")
    permission = db.scalar(select(Permission).where(
        Permission.requester_administration_id == administration.id,
        Permission.question_id == question.id,
    ))
    if permission is None or permission.status != "approved" or not permission.active:
        raise HTTPException(status_code=409, detail="Aucun droit validé à suspendre")
    permission.active = False
    permission.status = "suspended"
    try:
        provider_code = _question_provider_code(db, question)
        if provider_code:
            XRoadSync().revoke_access(administration.code, provider_code, question.service_code)
    except (XRoadSyncError, httpx.HTTPError) as error:
        raise HTTPException(status_code=503, detail=f"Révocation X-Road impossible : {error}") from error
    _audit(db, administration, principal, "Droit d’échange suspendu", question.description)
    db.commit()
    return {"question_code": question.code, "status": permission.status}


@router.put("/registry")
def save_registry(
    body: RegistryInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    registry = _primary_registry(db, administration, create=True)
    assert registry is not None
    registry.name = body.name.strip()
    registry.base_url = body.url
    registry.last_test_at = None
    registry.last_test_success = None
    _audit(db, administration, principal, "Connexion du registre enregistrée", registry.name,
           "URL conservée comme configuration, aucun secret transmis")
    db.commit()
    return _registry_payload(registry)


@router.post("/registry/test")
def test_registry(
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    registry = _primary_registry(db, administration)
    if registry is None or not registry.base_url:
        raise HTTPException(status_code=409, detail="Enregistrez d’abord l’URL du registre")
    success = False
    try:
        response = httpx.get(f"{registry.base_url.rstrip('/')}/health", timeout=3.0)
        success = response.status_code == 200 and response.json().get("status") == "up"
    except (httpx.HTTPError, ValueError, TypeError):
        success = False

    registry.last_test_at = datetime.now(timezone.utc)
    registry.last_test_success = success
    outcome = "registre disponible" if success else "registre indisponible"
    _audit(db, administration, principal, "Test réel du registre", registry.name,
           f"{outcome}; requête HTTP GET /health")
    db.commit()
    return {"at": registry.last_test_at, "success": success, "simulated": False}


@router.post("/services", status_code=status.HTTP_201_CREATED)
def create_offered_service(
    body: ServiceInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    registry = _primary_registry(db, administration, create=True)
    assert registry is not None
    if not registry.base_url:
        raise HTTPException(status_code=409, detail="Configurez l’adresse de votre API dans la connexion du registre avant de déclarer un service")
    existing = db.scalar(select(RegistryService).where(
        RegistryService.registry_id == registry.id,
        RegistryService.code == body.code,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="Ce code de service existe déjà")
    try:
        XRoadSync().publish_service(administration.code, body.code, registry.base_url)
    except (XRoadSyncError, httpx.HTTPError) as error:
        raise HTTPException(status_code=503, detail=f"Publication X-Road impossible : {error}") from error
    service = RegistryService(registry_id=registry.id, code=body.code,
                              title=body.title, description=body.description, active=True)
    db.add(service)
    db.flush()
    # A declared API must also be selectable as a business verification.
    db.add(Question(code=f"service_{service.id.hex}", registry_id=registry.id,
                    service_code=service.code, response_key=body.response_key,
                    description=service.title, active=True))
    _audit(db, administration, principal, "Service fournisseur déclaré", service.title,
           "Réponse minimale booléenne déclarée; le connecteur reste à implémenter")
    db.commit()
    db.refresh(service)
    return {"id": str(service.id), "code": service.code, "title": service.title,
            "description": service.description, "active": service.active}


@router.patch("/services/{service_id}/active")
def set_service_active(
    service_id: UUID,
    body: ActiveInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    service = db.get(RegistryService, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service introuvable")
    registry = db.get(Registry, service.registry_id)
    if registry is None or registry.administration_id != administration.id:
        raise HTTPException(status_code=404, detail="Service introuvable")
    try:
        XRoadSync().set_service_active(administration.code, service.code, body.active)
    except (XRoadSyncError, httpx.HTTPError) as error:
        raise HTTPException(status_code=503, detail=f"Synchronisation X-Road impossible : {error}") from error
    service.active = body.active
    for question in db.scalars(select(Question).where(
        Question.registry_id == registry.id, Question.service_code == service.code,
    )).all():
        question.active = body.active
    _audit(db, administration, principal,
           "Service fournisseur activé" if body.active else "Service fournisseur désactivé", service.title)
    db.commit()
    return {"id": str(service.id), "active": service.active}


@router.post("/agents", status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreateInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    phone = re.sub(r"\s", "", body.phone)
    if not re.fullmatch(r"[0-9]{8}", phone):
        raise HTTPException(status_code=422, detail="Le téléphone doit contenir les 8 chiffres nationaux")
    result = KeycloakAdminClient().create_agent(
        name=body.name,
        phone=phone,
        pin=body.pin,
        administration_code=administration.code,
    )
    _audit(db, administration, principal, "Compte agent créé", body.name,
           f"Téléphone se terminant par {phone[-2:]}; le PIN n’est pas journalisé")
    db.commit()
    return _agent_payload(result)


@router.get("/agents")
def list_agents(
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    return [_agent_payload(item) for item in KeycloakAdminClient().list_agents(administration.code)]


@router.patch("/agents/{agent_id}/active")
def set_agent_active(
    agent_id: UUID,
    body: ActiveInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    agent = KeycloakAdminClient().set_agent_enabled(str(agent_id), body.active, administration.code)
    _audit(db, administration, principal,
           "Compte agent réactivé" if body.active else "Compte agent suspendu", agent["name"])
    db.commit()
    return _agent_payload(agent)


@router.put("/agents/{agent_id}/pin")
def reset_agent_pin(
    agent_id: UUID,
    body: PinResetInput,
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    client = KeycloakAdminClient()
    client.reset_agent_pin(str(agent_id), body.pin, administration.code)
    _audit(db, administration, principal, "PIN agent réinitialisé", str(agent_id), "PIN non journalisé")
    db.commit()
    return {"id": str(agent_id), "pin_reset": True}


@router.get("/audit")
def list_admin_audit(
    search: str | None = Query(default=None, max_length=160),
    actor_role: str | None = Query(default=None, pattern="^(local-admin|agent|citizen|system)$"),
    limit: int = Query(default=200, ge=1, le=500),
    principal: Principal = Depends(require_role("local-admin")),
    db: Session = Depends(get_db),
):
    administration = _administration(db, principal)
    entries = []
    if actor_role in {None, "local-admin"}:
        query = select(AdministrationAuditEvent).where(
            AdministrationAuditEvent.administration_id == administration.id,
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(or_(
                AdministrationAuditEvent.actor_name.ilike(pattern),
                AdministrationAuditEvent.action.ilike(pattern),
                AdministrationAuditEvent.target.ilike(pattern),
                AdministrationAuditEvent.detail.ilike(pattern),
            ))
        for event in db.scalars(query.order_by(AdministrationAuditEvent.occurred_at.desc()).limit(limit)).all():
            entries.append({"id": str(event.id), "at": event.occurred_at, "actor": event.actor_name,
                            "role": event.actor_role, "action": event.action,
                            "target": event.target, "detail": event.detail})

    if actor_role in {None, "agent", "citizen", "system"}:
        # Événements des dossiers de l'administration, lus dans la couche journal.
        try:
            events = journal().search(requester_code=administration.code, actor_type=actor_role,
                                      q=search.strip() if search else None, order="desc", limit=limit)
        except JournalUnavailable as error:
            raise HTTPException(status_code=503, detail="Journal de traçabilité indisponible") from error
        for event in events:
            entries.append({"id": event["id"], "at": datetime.fromisoformat(event["occurred_at"]),
                            "actor": event.get("actor_ref") or event["actor_type"],
                            "role": event["actor_type"], "action": event["event_type"],
                            "target": (event.get("case_id") or "")[:8].upper(),
                            "detail": event["purpose"]})
    def moment(item: dict) -> datetime:
        # Dates du journal avec fuseau, dates locales parfois sans (SQLite) : comparées en UTC.
        at = item["at"] or datetime.min
        return at if at.tzinfo else at.replace(tzinfo=timezone.utc)

    entries.sort(key=moment, reverse=True)
    return entries[:limit]
