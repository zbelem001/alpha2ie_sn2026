"""Routes métier MVP, protégées par des jetons Bearer Keycloak."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Administration,
    AuditEvent,
    Case,
    ConsentOtpChallenge,
    RegistrationOtpChallenge,
    CitizenDocumentIdentifier,
    CitizenIdentityLink,
    Consent,
    ConsentQuestion,
    Notification,
    Permission,
    Procedure,
    ProcedureQuestion,
    Question,
    Registry,
    RegistryRequest,
    RequestAttempt,
)
from app.security import Principal, get_current_principal, require_any_role, require_role
from app.sms import dispatch_sms_notification
from app.sms_provider import (
    InfobipOtpProvider,
    SmsConfigurationError,
    SmsDeliveryError,
    build_sms_provider,
)
from app.sms_templates import (
    render_consent_request,
)
from app.identifiers import IdentifierVaultError, decrypt_identifier, encrypt_identifier, identifier_digest
from app.otp_simulation import (
    OtpSimulationConfigurationError,
    code_for as simulated_otp_code,
    code_matches as simulated_otp_matches,
    delivery_mode as otp_delivery_mode,
    digest_code as simulated_otp_digest,
)

router = APIRouter(prefix="/v1")
logger = logging.getLogger(__name__)
REQUEST_LEASE_SECONDS = 60
CONSENT_OTP_TTL = timedelta(minutes=5)
CONSENT_OTP_RESEND_DELAY = timedelta(seconds=30)
CONSENT_OTP_MAX_ATTEMPTS = 5
CONSENT_OTP_MAX_SENDS_PER_HOUR = 5
IDENTIFIER_REGISTRIES = {
    "cnib_number": "BF/GOV/ONI/CNIB",
    "birth_act_number": "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
    "criminal_record_number": "BF/GOV/JUSTICE/REGISTRES",
    "nationality_reference": "BF/GOV/JUSTICE/REGISTRES",
    "payment_reference": "BF/GOV/TRESOR/PAIEMENTS",
    "loss_report_number": "BF/GOV/POLICE/DECLARATIONS",
}
QUESTION_IDENTIFIER_TYPES = {
    "candidate_minimum_age": "birth_act_number",
    "candidate_nationality": "nationality_reference",
    "passport_cnib_valid": "cnib_number",
    "passport_birth_act_found": "birth_act_number",
    "passport_nationality": "nationality_reference",
    "passport_criminal_record_current": "criminal_record_number",
    "criminal_record_indicator": "criminal_record_number",
    "passport_fiscal_stamp_paid": "payment_reference",
    "loss_declared": "loss_report_number",
}


class DocumentIdentifierInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    identifier_type: str = Field(pattern="^(cnib_number|birth_act_number|criminal_record_number|nationality_reference|payment_reference|loss_report_number)$")
    value: str = Field(min_length=4, max_length=80, pattern="^[A-Za-z0-9][A-Za-z0-9./_-]*$")

    def normalized_value(self) -> str:
        return self.value.strip().upper()


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    procedure_code: str = Field(validation_alias=AliasChoices("procedure_code", "procedureCode"))
    consent_channel: str = Field(default="web", pattern="^(assisted|web)$", validation_alias=AliasChoices("consent_channel", "channel"))
    phone_number: str | None = Field(default=None, max_length=24, validation_alias=AliasChoices("phone_number", "phone"))
    subject_ref: str | None = Field(default=None, min_length=1, max_length=160, validation_alias=AliasChoices("subject_ref", "subjectRef"))
    applicant_name: str = Field(default="Citoyen", min_length=1, max_length=100, validation_alias=AliasChoices("applicant_name", "applicantName"))
    citizen_identifier: DocumentIdentifierInput | None = None
    registry_identifiers: list[DocumentIdentifierInput] = Field(default_factory=list, max_length=8)
    references: dict[str, str] = Field(default_factory=dict, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def _accept_frontend_references(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        references = data.pop("references", {})
        if references and not data.get("registry_identifiers"):
            document_types = {
                "cnib": "cnib_number", "birth": "birth_act_number",
                "nationality": "nationality_reference", "criminal": "criminal_record_number",
                "payment": "payment_reference", "loss": "loss_report_number",
            }
            if (not isinstance(references, dict)
                    or any(key not in document_types for key in references)
                    or any(not isinstance(item, str) for item in references.values())):
                raise ValueError("Une ou plusieurs références de document sont inconnues")
            data["registry_identifiers"] = [
                {"identifier_type": document_types[key], "value": item}
                for key, item in references.items() if item.strip()
            ]
        return data

    @model_validator(mode="after")
    def _requires_citizen_locator(self):
        if not self.subject_ref and self.citizen_identifier is None and not self.registry_identifiers and not self.phone_number:
            raise ValueError("une référence de citoyen ou de document est requise")
        if self.subject_ref and self.citizen_identifier is not None:
            raise ValueError("Fournir subject_ref ou citizen_identifier, pas les deux")
        types = [item.identifier_type for item in self.registry_identifiers]
        if len(types) != len(set(types)):
            raise ValueError("Un seul identifiant est autorisé par type")
        return self


class CitizenIdentifiersUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    confirmed: bool
    identifiers: list[DocumentIdentifierInput] = Field(default_factory=list, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def _accept_frontend_document_profile(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        references = data.pop("references", {})
        if references and not data.get("identifiers"):
            document_types = {
                "cnib": "cnib_number", "birth": "birth_act_number",
                "nationality": "nationality_reference", "criminal": "criminal_record_number",
                "payment": "payment_reference", "loss": "loss_report_number",
            }
            if (not isinstance(references, dict)
                    or any(key not in document_types for key in references)
                    or any(not isinstance(item, str) for item in references.values())):
                raise ValueError("Une ou plusieurs références de document sont inconnues")
            data["identifiers"] = [
                {"identifier_type": document_types[key], "value": item}
                for key, item in references.items() if item.strip()
            ]
        return data

    @model_validator(mode="after")
    def _unique_types(self):
        types = [item.identifier_type for item in self.identifiers]
        if len(types) != len(set(types)):
            raise ValueError("Un seul identifiant est autorisé par type")
        return self


class ConsentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    decision: str = Field(pattern="^(granted|refused)$")
    question_codes: list[str] = Field(min_length=1, validation_alias=AliasChoices("question_codes", "questionCodes"))
    notice_version: str = Field(validation_alias=AliasChoices("notice_version", "noticeVersion"))
    channel: str = Field(pattern="^(in_person|web|assisted)$")
    expires_at: datetime | None = None


class ConsentOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resend: bool = False


class ConsentOtpVerify(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern="^[0-9]{6}$")


class ConsentChannelChange(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    consent_channel: str = Field(pattern="^(assisted|web)$", validation_alias=AliasChoices("consent_channel", "channel"))


class RegistrationOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    phone_number: str = Field(min_length=8, max_length=16, validation_alias=AliasChoices("phone_number", "phone"))


class RegistrationOtpVerify(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    challenge_id: UUID = Field(validation_alias=AliasChoices("challenge_id", "challengeId"))
    code: str = Field(pattern="^[0-9]{6}$")


class IdentityLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_ref: str = Field(min_length=1, max_length=160)
    confirmed: bool


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
    case = db.get(Case, request.case_id)
    subject: dict[str, str] = {}
    parameters: dict[str, str] = {}
    # Titulaire attendu, transmis dès qu'il est connu : avec une référence de pièce, le registre
    # vérifie que la fiche désignée appartient bien à cette personne (un faux lien est pire que
    # pas de lien). Sans lui, le casier d'un tiers saisi par erreur était attribué au citoyen.
    if case.subject_ref.startswith("ACTE:"):
        subject["pivot_id"] = case.subject_ref
    if request.lookup_identifier_ciphertext:
        try:
            parameters = {
                "identifier_type": request.lookup_identifier_type or "",
                "document_identifier": decrypt_identifier(request.lookup_identifier_ciphertext),
            }
        except IdentifierVaultError as error:
            raise HTTPException(status_code=503, detail="Impossible de déchiffrer l’identifiant de registre") from error
    return {
        "question": question,
        "registry": registry,
        "payload": {
            "request_id": str(request.id),
            "procedure": db.get(Procedure, db.get(Case, request.case_id).procedure_id).code,
            "subject": subject,
            "parameters": parameters,
        },
        "organization": administration.code,
    }


def _serialize_check(db: Session, request: RegistryRequest) -> dict:
    question = db.get(Question, request.question_id)
    registry = db.get(Registry, question.registry_id) if question else None
    administration = db.get(Administration, registry.administration_id) if registry else None
    procedure_link = db.scalar(select(ProcedureQuestion).join(
        Case, Case.procedure_id == ProcedureQuestion.procedure_id
    ).where(Case.id == request.case_id, ProcedureQuestion.question_id == request.question_id))
    document_key = (procedure_link.document_type if procedure_link else None) or {
        "cnib_number": "cnib", "birth_act_number": "birth", "nationality_reference": "nationality",
        "criminal_record_number": "criminal", "payment_reference": "payment", "loss_report_number": "loss",
    }.get(QUESTION_IDENTIFIER_TYPES.get(question.code, ""), "") if question else ""
    result = request.minimal_result
    if isinstance(result, dict):
        result = result.get(question.response_key) if question else None
    if not isinstance(result, bool):
        result = None
    document = {
        "key": document_key,
        "label": (procedure_link.document_label if procedure_link else None) or (question.description if question else "Document"),
        "provider": administration.name if administration else "",
        "hint": (procedure_link.document_hint if procedure_link else None) or "",
    }
    return {
        "question_code": question.code,
        "questionCode": question.code,
        "label": question.description,
        "registry": administration.name if administration else "",
        "document": document,
        "required": procedure_link.required if procedure_link else True,
        "status": "queued" if request.status == "pending" else request.status,
        "result": result,
        "message": None,
        "attempt_count": request.attempt_count,
        "attemptCount": request.attempt_count,
    }


def _serialize_case(db: Session, case: Case) -> dict:
    procedure = db.get(Procedure, case.procedure_id)
    administration = db.get(Administration, case.requester_administration_id)
    identity_link = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.subject_ref == case.subject_ref))
    checks = db.scalars(select(RegistryRequest).where(RegistryRequest.case_id == case.id)).all()
    created_at = _utc(case.created_at) if case.created_at else None
    reference_prefix = "PAS" if procedure and "passeport" in procedure.code else "DOS"
    reference = f"{reference_prefix}-{created_at.year if created_at else datetime.now(timezone.utc).year}-{case.id.hex[:6].upper()}"
    channel = case.consent_channel
    status_value = "pending" if case.status == "in_progress" else "rejected" if case.status == "cancelled" else case.status
    return {
        "id": str(case.id),
        "reference": reference,
        "procedure_code": procedure.code,
        "procedureCode": procedure.code,
        "createdAt": created_at.isoformat() if created_at else None,
        "applicantName": case.applicant_name,
        "phone": identity_link.phone_number if identity_link else "",
        "procedureTitle": procedure.title,
        "procedurePurpose": procedure.purpose,
        "procedureVersion": procedure.config_version,
        "consentDays": procedure.consent_days,
        "channel": channel,
        "authorizationId": f"consent-{case.id}",
        "subject_ref": case.subject_ref,
        "status": status_value,
        "consent_channel": case.consent_channel,
        "checks": [_serialize_check(db, item) for item in checks],
        "created_at": created_at,
    }


def _case_or_404(db: Session, case_id: UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return case


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _consent_scope(db: Session, case: Case) -> tuple[list[tuple[ProcedureQuestion, Question]], str]:
    procedure_links = db.scalars(
        select(ProcedureQuestion)
        .where(ProcedureQuestion.procedure_id == case.procedure_id)
        .order_by(ProcedureQuestion.position)
    ).all()
    scope = []
    for link in procedure_links:
        question = db.get(Question, link.question_id)
        request = db.scalar(select(RegistryRequest).where(
            RegistryRequest.case_id == case.id,
            RegistryRequest.question_id == question.id,
        ))
        scope.append((link, question, request))
    snapshot = [
        {
            "question_code": question.code,
            "description": question.description,
            "required": link.required,
            "identifier_type": request.lookup_identifier_type if request else None,
            "identifier_ciphertext": request.lookup_identifier_ciphertext if request else None,
        }
        for link, question, request in scope
    ]
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return [(link, question) for link, question, _ in scope], digest


def _serialize_consent_challenge(challenge: ConsentOtpChallenge, phone: str) -> dict:
    masked_phone = f"{phone[:5]}{'*' * max(0, len(phone) - 7)}{phone[-2:]}"
    simulated = challenge.code_digest is not None
    result = {
        "challenge_id": str(challenge.id),
        "challengeId": str(challenge.id),
        "case_id": str(challenge.case_id),
        "caseId": str(challenge.case_id),
        "phone": masked_phone,
        "expires_at": _utc(challenge.expires_at),
        "expiresAt": int(_utc(challenge.expires_at).timestamp() * 1000),
        "resend_after": _utc(challenge.resend_after),
        "resendAt": int(_utc(challenge.resend_after).timestamp() * 1000),
        "referencesSnapshot": challenge.scope_digest,
        "delivery_status": challenge.delivery_status,
        "mode": "simulation" if simulated else "sms",
        "message": (
            "Code OTP de démonstration généré par le backend; aucun SMS n’a été envoyé. "
            "Ce mode ne vérifie pas la possession du téléphone."
            if simulated else "Un code d’accord a été envoyé par SMS. Il n’est jamais affiché dans l’espace agent."
        ),
    }
    if simulated:
        try:
            if os.getenv("OTP_SIMULATION_EXPOSE_CODE", "false").strip().lower() != "true":
                raise OtpSimulationConfigurationError("otp_simulation_code_exposure_disabled")
            result["demo_code"] = simulated_otp_code(challenge.id, "consent")
            result["code"] = result["demo_code"]
        except OtpSimulationConfigurationError as error:
            raise HTTPException(status_code=503, detail="Le code de démonstration n’est plus disponible; demandez-en un nouveau.") from error
    return result


def _serialize_registration_challenge(challenge: RegistrationOtpChallenge) -> dict:
    simulated = challenge.code_digest is not None
    result = {
        "challenge_id": str(challenge.id),
        "challengeId": str(challenge.id),
        "phone": _mask_phone(challenge.phone_number),
        "expires_at": _utc(challenge.expires_at),
        "expiresAt": int(_utc(challenge.expires_at).timestamp() * 1000),
        "resend_after": _utc(challenge.resend_after),
        "resendAt": int(_utc(challenge.resend_after).timestamp() * 1000),
        "mode": "simulation" if simulated else "sms",
        "message": (
            "Code OTP de démonstration généré par le backend; aucun SMS n’a été envoyé. "
            "Cette simulation ne vérifie pas la possession du téléphone."
            if simulated else "Le code d’inscription a été envoyé par SMS."
        ),
    }
    if simulated:
        try:
            if os.getenv("OTP_SIMULATION_EXPOSE_CODE", "false").strip().lower() != "true":
                raise OtpSimulationConfigurationError("otp_simulation_code_exposure_disabled")
            result["demo_code"] = simulated_otp_code(challenge.id, "registration")
            result["code"] = result["demo_code"]
        except OtpSimulationConfigurationError as error:
            raise HTTPException(status_code=503, detail="Le code de démonstration n’est plus disponible; demandez-en un nouveau.") from error
    return result


def _identifier_records(db: Session, principal_sub: str) -> list[CitizenDocumentIdentifier]:
    return db.scalars(
        select(CitizenDocumentIdentifier)
        .where(CitizenDocumentIdentifier.principal_sub == principal_sub)
        .order_by(CitizenDocumentIdentifier.identifier_type)
    ).all()


def _find_identifier(db: Session, identifier: DocumentIdentifierInput) -> CitizenDocumentIdentifier | None:
    digest = identifier_digest(identifier.identifier_type, identifier.normalized_value())
    return db.scalar(
        select(CitizenDocumentIdentifier).where(CitizenDocumentIdentifier.identifier_digest == digest)
    )


def _citizen_reference_for_case(
    db: Session, principal: Principal, body: CaseCreate
) -> tuple[str, dict[str, str]]:
    locator = body.citizen_identifier
    if locator is None and not body.subject_ref:
        if body.phone_number:
            phone_number = _normalize_burkina_phone(body.phone_number)
            if phone_number is None:
                raise HTTPException(status_code=422, detail="Le numéro de téléphone doit être international ou contenir 8 chiffres BF")
            phone_links = db.scalars(
                select(CitizenIdentityLink).where(CitizenIdentityLink.phone_number == phone_number)
            ).all()
            if not phone_links:
                raise HTTPException(status_code=404, detail="Aucun compte citoyen n’est rattaché à ce numéro")
            if len(phone_links) > 1:
                raise HTTPException(status_code=409, detail="Ce numéro est lié à plusieurs comptes citoyens")
            subject_ref = phone_links[0].subject_ref
        elif body.registry_identifiers:
            matches = []
            for item in body.registry_identifiers:
                try:
                    record = _find_identifier(db, item)
                except IdentifierVaultError as error:
                    raise HTTPException(status_code=503, detail="Le chiffrement des identifiants n’est pas configuré") from error
                if record is not None:
                    matches.append(record.subject_ref)
            if not matches:
                raise HTTPException(status_code=404, detail="Aucun citoyen ne correspond aux références fournies")
            if len(set(matches)) != 1:
                raise HTTPException(status_code=422, detail="Les références fournies ne désignent pas le même citoyen")
            subject_ref = matches[0]
        else:
            raise HTTPException(status_code=422, detail="Une référence de citoyen ou un numéro lié est requis")
    elif locator is not None:
        try:
            record = _find_identifier(db, locator)
        except IdentifierVaultError as error:
            raise HTTPException(status_code=503, detail="Le chiffrement des identifiants n’est pas configuré") from error
        if record is None:
            raise HTTPException(status_code=404, detail="Aucun citoyen ne correspond à cet identifiant")
        subject_ref = record.subject_ref
    else:
        subject_ref = body.subject_ref.strip().upper()

    saved = db.scalars(
        select(CitizenDocumentIdentifier).where(CitizenDocumentIdentifier.subject_ref == subject_ref)
    ).all()
    by_type = {item.identifier_type: item for item in saved}
    requested = {item.identifier_type: item for item in body.registry_identifiers}
    selected: dict[str, str] = {}
    for identifier_type, item in requested.items():
        try:
            record = _find_identifier(db, item)
        except IdentifierVaultError as error:
            raise HTTPException(status_code=503, detail="Le chiffrement des identifiants n’est pas configuré") from error
        if record is not None and record.subject_ref != subject_ref:
            raise HTTPException(status_code=422, detail="Chaque identifiant de registre doit appartenir au citoyen recherché")
        if record is None and not body.phone_number:
            raise HTTPException(status_code=422, detail="Chaque identifiant doit être enregistré au profil du citoyen ou accompagné de son numéro lié")
        selected[identifier_type] = item.normalized_value()
    for identifier_type, record in by_type.items():
        if identifier_type not in selected and identifier_type not in requested:
            try:
                selected[identifier_type] = decrypt_identifier(record.identifier_ciphertext)
            except IdentifierVaultError as error:
                raise HTTPException(status_code=503, detail="Impossible de déchiffrer les identifiants enregistrés") from error
    return subject_ref, selected


def _normalize_burkina_phone(phone: str) -> str | None:
    normalized = re.sub(r"\s", "", phone)
    if re.fullmatch(r"[0-9]{8}", normalized):
        normalized = "+226" + normalized
    return normalized if re.fullmatch(r"\+[1-9][0-9]{7,14}", normalized) else None


def _mask_phone(phone: str) -> str:
    return f"{phone[:5]}{'*' * max(0, len(phone) - 7)}{phone[-2:]}"


def _authorize_case_access(case: Case, db: Session, principal: Principal) -> None:
    if "agent" in principal.roles or "local-admin" in principal.roles:
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
    procedures = db.scalars(select(Procedure).where(
        Procedure.active.is_(True), Procedure.published.is_(True)
    )).all()
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
            "purpose": procedure.purpose,
            "version": procedure.config_version,
            "consentDays": procedure.consent_days,
            "active": procedure.active,
            "published": procedure.published,
            "questions": [
                {"code": (question := db.get(Question, link.question_id)).code,
                 "description": question.description, "required": link.required}
                for link in links
            ],
            "checks": [
                {
                    "questionCode": (question := db.get(Question, link.question_id)).code,
                    "required": link.required,
                    "document": {
                        "key": link.document_type or {
                            "cnib_number": "cnib", "birth_act_number": "birth",
                            "nationality_reference": "nationality", "criminal_record_number": "criminal",
                            "payment_reference": "payment", "loss_report_number": "loss",
                        }.get(QUESTION_IDENTIFIER_TYPES.get(question.code, ""), ""),
                        "label": link.document_label or question.description,
                        "provider": (
                            db.get(Administration, db.get(Registry, question.registry_id).administration_id).name
                            if db.get(Registry, question.registry_id) else ""
                        ),
                        "hint": link.document_hint or "",
                    },
                }
                for link in links
            ],
        })
    return result


@router.get("/citizen/identity-link")
def get_citizen_identity_link(
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    link = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == principal.subject))
    subject_ref = link.subject_ref if link else principal.citizen_ref
    # A token claim alone does not establish the verified phone-to-reference
    # route needed for notifications; POST records that association explicitly.
    return {"linked": link is not None, "subject_ref": subject_ref, "subjectRef": subject_ref}


@router.get("/citizen/identifiers")
def get_citizen_identifiers(
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    link = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == principal.subject))
    if link is None:
        return {"linked": False, "subject_ref": None, "subjectRef": None, "identifiers": [], "references": {}}
    try:
        identifiers = [
            {"identifier_type": item.identifier_type, "value": decrypt_identifier(item.identifier_ciphertext)}
            for item in _identifier_records(db, principal.subject)
        ]
    except IdentifierVaultError as error:
        raise HTTPException(status_code=503, detail="Impossible de déchiffrer les identifiants enregistrés") from error
    reference_keys = {
        "cnib_number": "cnib", "birth_act_number": "birth", "nationality_reference": "nationality",
        "criminal_record_number": "criminal", "payment_reference": "payment", "loss_report_number": "loss",
    }
    return {
        "linked": True, "subject_ref": link.subject_ref, "subjectRef": link.subject_ref,
        "identifiers": identifiers,
        "references": {reference_keys[item["identifier_type"]]: item["value"] for item in identifiers},
    }


@router.put("/citizen/identifiers")
def save_citizen_identifiers(
    body: CitizenIdentifiersUpdate,
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    if not body.confirmed:
        raise HTTPException(status_code=422, detail="Veuillez confirmer que les références saisies sont exactes")
    if not principal.phone_number or not re.fullmatch(r"\+[1-9][0-9]{7,14}", principal.phone_number):
        raise HTTPException(status_code=422, detail="Un numéro de téléphone au format international est requis")

    link = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == principal.subject))
    if link is None:
        subject_ref = f"CITIZEN:{uuid4().hex.upper()}"
        link = CitizenIdentityLink(
            principal_sub=principal.subject,
            subject_ref=subject_ref,
            phone_number=principal.phone_number,
        )
        db.add(link)
        db.flush()
    else:
        link.phone_number = principal.phone_number

    existing = {item.identifier_type: item for item in _identifier_records(db, principal.subject)}
    wanted = {item.identifier_type: item for item in body.identifiers}
    for identifier_type, record in existing.items():
        if identifier_type not in wanted:
            db.delete(record)
    try:
        for identifier_type, item in wanted.items():
            value = item.normalized_value()
            digest = identifier_digest(identifier_type, value)
            if any(other.subject_ref != link.subject_ref for other in db.scalars(
                select(CitizenDocumentIdentifier).where(CitizenDocumentIdentifier.identifier_digest == digest)
            ).all()):
                raise HTTPException(status_code=409, detail="Cette référence est déjà associée à un autre compte")
            record = existing.get(identifier_type)
            values = {
                "subject_ref": link.subject_ref,
                "registry_code": IDENTIFIER_REGISTRIES[identifier_type],
                "identifier_ciphertext": encrypt_identifier(value),
                "identifier_digest": digest,
            }
            if record is None:
                db.add(CitizenDocumentIdentifier(
                    principal_sub=principal.subject,
                    identifier_type=identifier_type,
                    **values,
                ))
            else:
                for key, field_value in values.items():
                    setattr(record, key, field_value)
        db.commit()
    except IdentifierVaultError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="Le chiffrement des identifiants n’est pas configuré") from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette référence est déjà associée à un autre compte") from error
    reference_keys = {
        "cnib_number": "cnib", "birth_act_number": "birth", "nationality_reference": "nationality",
        "criminal_record_number": "criminal", "payment_reference": "payment", "loss_report_number": "loss",
    }
    return {
        "linked": True, "subject_ref": link.subject_ref, "subjectRef": link.subject_ref,
        "identifier_types": sorted(wanted),
        "references": {reference_keys[key]: item.normalized_value() for key, item in wanted.items()},
    }


@router.post("/citizen/identity-link", status_code=status.HTTP_201_CREATED)
def link_citizen_identity(
    body: IdentityLinkCreate,
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    subject_ref = body.subject_ref.strip().upper()
    if not body.confirmed:
        raise HTTPException(status_code=422, detail="Veuillez confirmer la référence saisie")
    if not re.fullmatch(r"ACTE:[A-Z]+:[0-9]{4}:[0-9]{5}", subject_ref):
        raise HTTPException(status_code=422, detail="La référence doit respecter le format ACTE:VILLE:AAAA:NNNNN")
    if not principal.phone_number or not principal.phone_number_verified:
        raise HTTPException(status_code=403, detail="Un numéro de téléphone vérifié est requis avant le rattachement")
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", principal.phone_number):
        raise HTTPException(status_code=422, detail="Le numéro vérifié doit être au format international, par exemple +226XXXXXXXX")
    if principal.citizen_ref and principal.citizen_ref != subject_ref:
        raise HTTPException(status_code=409, detail="Une autre référence est déjà associée à ce compte")

    by_account = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == principal.subject))
    by_reference = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.subject_ref == subject_ref))
    if by_account:
        if by_account.subject_ref != subject_ref:
            raise HTTPException(status_code=409, detail="Une autre référence est déjà associée à ce compte")
        if by_account.phone_number != principal.phone_number:
            by_account.phone_number = principal.phone_number
            db.commit()
        return {"linked": True, "subject_ref": subject_ref}
    if by_reference and by_reference.principal_sub != principal.subject:
        raise HTTPException(status_code=409, detail="Cette référence est déjà associée à un autre compte")

    from connectors import build_connector

    try:
        identity_reply = build_connector().query(
            "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
            "identity",
            {"procedure": "citizen_identity_link", "subject": {"pivot_id": subject_ref}},
        )
    except Exception as error:
        raise HTTPException(status_code=503, detail="Le registre de démonstration est indisponible") from error
    identity_status = identity_reply.get("status")
    if identity_status == "not_found":
        raise HTTPException(status_code=404, detail="Référence absente du jeu de données de démonstration")
    if identity_status == "ambiguous":
        raise HTTPException(status_code=409, detail="Référence ambiguë dans le jeu de données de démonstration")
    if identity_status != "ok" or not isinstance(identity_reply.get("data"), dict) or identity_reply["data"].get("pivot_id") != subject_ref:
        raise HTTPException(status_code=422, detail="La référence n’a pas pu être validée dans le jeu de données")

    link = CitizenIdentityLink(
        principal_sub=principal.subject,
        subject_ref=subject_ref,
        phone_number=principal.phone_number,
    )
    db.add(link)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette référence ou ce compte vient d’être associé") from error
    return {"linked": True, "subject_ref": subject_ref}


@router.post("/auth/registration/otp", status_code=status.HTTP_202_ACCEPTED)
def request_registration_otp(
    body: RegistrationOtpRequest,
    db: Session = Depends(get_db),
):
    phone_number = _normalize_burkina_phone(body.phone_number)
    if phone_number is None:
        raise HTTPException(status_code=422, detail="Le numéro doit être international ou contenir 8 chiffres BF")

    now = datetime.now(timezone.utc)
    db.execute(delete(RegistrationOtpChallenge).where(
        RegistrationOtpChallenge.created_at < now - timedelta(days=1)
    ))
    latest = db.scalar(
        select(RegistrationOtpChallenge)
        .where(RegistrationOtpChallenge.phone_number == phone_number)
        .order_by(RegistrationOtpChallenge.created_at.desc())
    )
    if latest and latest.verified_at is None and _utc(latest.expires_at) > now:
        if _utc(latest.resend_after) > now:
            return _serialize_registration_challenge(latest)
    recent_count = db.scalar(select(func.count(RegistrationOtpChallenge.id)).where(
        RegistrationOtpChallenge.phone_number == phone_number,
        RegistrationOtpChallenge.created_at >= now - timedelta(hours=1),
    )) or 0
    if recent_count >= CONSENT_OTP_MAX_SENDS_PER_HOUR:
        raise HTTPException(status_code=429, detail="La limite d’envoi de codes pour ce numéro est atteinte")

    try:
        mode = otp_delivery_mode()
    except OtpSimulationConfigurationError as error:
        raise HTTPException(status_code=503, detail="La simulation OTP n’est pas configurée correctement") from error
    challenge_id = uuid4()
    provider_pin_id = None
    code_digest = None
    if mode == "simulated":
        code_digest = simulated_otp_digest(
            challenge_id, "registration", simulated_otp_code(challenge_id, "registration")
        )
    else:
        try:
            otp_provider = InfobipOtpProvider.from_environment()
            if _normalize_burkina_phone(otp_provider.settings.test_phone_number) != phone_number:
                raise HTTPException(
                    status_code=409,
                    detail="En mode d’essai, seuls les numéros vérifiés configurés dans Infobip peuvent recevoir le code.",
                )
            result = otp_provider.send_pin("registration", phone_number)
            provider_pin_id = result.pin_id
        except (SmsConfigurationError, SmsDeliveryError) as error:
            logger.warning("Registration OTP SMS failed: %s", getattr(error, "safe_code", str(error)))
            raise HTTPException(status_code=502, detail="Échec de l’envoi du code d’inscription par SMS") from error

    challenge = RegistrationOtpChallenge(
        id=challenge_id,
        phone_number=phone_number,
        provider_pin_id=provider_pin_id,
        code_digest=code_digest,
        expires_at=now + CONSENT_OTP_TTL,
        resend_after=now + CONSENT_OTP_RESEND_DELAY,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return _serialize_registration_challenge(challenge)


@router.post("/auth/registration/otp/verify")
def verify_registration_otp(
    body: RegistrationOtpVerify,
    db: Session = Depends(get_db),
):
    challenge = db.get(RegistrationOtpChallenge, body.challenge_id)
    if challenge is None or challenge.verified_at is not None:
        raise HTTPException(status_code=404, detail="Défi d’inscription introuvable ou déjà utilisé")
    now = datetime.now(timezone.utc)
    if _utc(challenge.expires_at) <= now or challenge.attempt_count >= CONSENT_OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=410, detail="Le code a expiré. Demandez-en un nouveau.")
    try:
        if challenge.code_digest is not None:
            verified = simulated_otp_matches(challenge.id, "registration", body.code, challenge.code_digest)
        elif challenge.provider_pin_id:
            verified = InfobipOtpProvider.from_environment().verify_pin(challenge.provider_pin_id, body.code)
        else:
            raise HTTPException(status_code=409, detail="Le défi OTP ne peut pas être vérifié")
    except OtpSimulationConfigurationError as error:
        raise HTTPException(status_code=503, detail="La configuration du code de démonstration est absente") from error
    except (SmsConfigurationError, SmsDeliveryError) as error:
        logger.warning("Registration OTP verification failed: %s", getattr(error, "safe_code", str(error)))
        raise HTTPException(status_code=502, detail="La vérification du code par Infobip a échoué") from error
    if not verified:
        challenge.attempt_count += 1
        if challenge.attempt_count >= CONSENT_OTP_MAX_ATTEMPTS:
            challenge.expires_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="Code incorrect")
    simulated = challenge.code_digest is not None
    challenge.verified_at = now
    challenge.code_digest = None
    challenge.provider_pin_id = None
    db.commit()
    return {
        "phone_verified": True,
        "phoneVerified": True,
        "phoneVerificationSimulated": simulated,
        "otp_validated": True,
        "otpValidated": True,
        "verification_mode": "simulation" if simulated else "sms",
        "verificationMode": "simulation" if simulated else "sms",
        "phone": _mask_phone(challenge.phone_number),
        "verified_at": challenge.verified_at,
        "verifiedAt": challenge.verified_at,
    }


@router.get("/cases")
def list_cases(
    case_status: str | None = None,
    caseStatus: str | None = Query(default=None, alias="caseStatus"),
    limit: int = 50,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    case_status = caseStatus if caseStatus is not None else case_status
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="La limite doit être comprise entre 1 et 100")
    query = select(Case)
    if case_status is not None:
        if case_status not in {"received", "in_progress", "pending", "completed", "rejected", "cancelled"}:
            raise HTTPException(status_code=422, detail="État de dossier invalide")
        query = query.where(Case.status == case_status)
    if "agent" in principal.roles or "local-admin" in principal.roles:
        if not principal.administration_code:
            raise HTTPException(status_code=403, detail="Jeton agent sans administration")
        administration = db.scalar(select(Administration).where(
            Administration.code == principal.administration_code,
            Administration.active.is_(True),
        ))
        if administration is None:
            raise HTTPException(status_code=403, detail="Administration agent inconnue ou inactive")
        query = query.where(Case.requester_administration_id == administration.id)
    elif "citizen" in principal.roles:
        if not principal.citizen_ref:
            raise HTTPException(status_code=403, detail="Jeton citoyen sans référence citoyen")
        query = query.where(Case.subject_ref == principal.citizen_ref)
    else:
        raise HTTPException(status_code=403, detail="Rôle insuffisant pour consulter les dossiers")
    cases = db.scalars(query.order_by(Case.created_at.desc()).limit(limit)).all()
    return [_serialize_case(db, case) for case in cases]


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreate,
    principal: Principal = Depends(require_any_role("agent", "local-admin")),
    db: Session = Depends(get_db),
):
    procedure = db.scalar(select(Procedure).where(
        Procedure.code == body.procedure_code,
        Procedure.active.is_(True),
        Procedure.published.is_(True),
    ))
    if not principal.administration_code:
        raise HTTPException(status_code=403, detail="Jeton agent sans administration")
    requester = db.scalar(select(Administration).where(Administration.code == principal.administration_code,
                                                       Administration.active.is_(True)))
    if procedure is None or requester is None:
        raise HTTPException(status_code=404, detail="Démarche ou administration inconnue")
    if requester.id != procedure.owner_administration_id:
        raise HTTPException(status_code=403, detail="Un agent ne peut ouvrir que les démarches de son administration")
    links = db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id)).all()
    if not links:
        raise HTTPException(status_code=409, detail="La démarche ne contient aucune vérification")
    subject_ref, submitted_identifiers = _citizen_reference_for_case(db, principal, body)
    if body.phone_number is not None:
        contact_phone = _normalize_burkina_phone(body.phone_number)
        identity_link = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.subject_ref == subject_ref))
        if contact_phone is None:
            raise HTTPException(status_code=422, detail="Le numéro de téléphone doit être international ou contenir 8 chiffres BF")
        if identity_link is None or contact_phone != identity_link.phone_number:
            raise HTTPException(status_code=409, detail="Le numéro ne correspond pas au contact rattaché au compte citoyen")
    case = Case(procedure_id=procedure.id, requester_administration_id=requester.id,
                subject_ref=subject_ref, applicant_name=body.applicant_name.strip() or "Citoyen",
                status="received", consent_channel=body.consent_channel)
    db.add(case)
    db.flush()
    for link in links:
        question = db.get(Question, link.question_id)
        identifier_type = QUESTION_IDENTIFIER_TYPES.get(question.code)
        identifier_value = submitted_identifiers.get(identifier_type) if identifier_type else None
        try:
            encrypted_identifier = encrypt_identifier(identifier_value) if identifier_value else None
        except IdentifierVaultError as error:
            db.rollback()
            raise HTTPException(status_code=503, detail="Le chiffrement des identifiants n’est pas configuré") from error
        db.add(RegistryRequest(case_id=case.id, question_id=question.id, status="queued",
                               idempotency_key=f"{case.id}:{question.code}",
                               lookup_identifier_type=identifier_type if identifier_value else None,
                               lookup_identifier_ciphertext=encrypted_identifier))
    _add_event(db, case, "case_created", procedure.code, outcome="received", actor_type="agent",
               actor_ref=requester.code)
    db.flush()
    notification_title = "Consentement requis"
    notification_message = (
        "Une demande de consentement vous attend pour votre démarche. "
        "Connectez-vous à la plateforme pour la consulter et donner votre réponse."
    )
    db.add(Notification(
        case_id=case.id,
        recipient_ref=case.subject_ref,
        channel="platform",
        title=notification_title,
        message=notification_message,
        delivery_status="delivered",
    ))
    sms_notification = None
    if body.consent_channel == "web":
        sms_provider = os.getenv("SMS_PROVIDER", "simulated").lower()
        sms_message = render_consent_request(procedure.title, case.id.hex[:8].upper())
        sms_delivery_status = "queued" if sms_provider == "infobip" and sms_message else "simulated"
        sms_delivery_error = None
        if sms_provider == "infobip" and sms_message is None:
            sms_delivery_status = "failed"
            sms_delivery_error = "sms_template_missing_data"
        sms_notification = Notification(
            case_id=case.id,
            recipient_ref=case.subject_ref,
            channel="sms",
            title=notification_title,
            message=sms_message or "",
            delivery_status=sms_delivery_status,
            delivery_error=sms_delivery_error,
        )
        db.add(sms_notification)
    _add_event(db, case, "consent_requested", procedure.code, outcome="notification_created",
               actor_type="system")
    db.commit()
    if sms_notification and sms_delivery_status == "queued":
        dispatch_sms_notification(db, sms_notification)
    db.refresh(case)
    return _serialize_case(db, case)


@router.post("/cases/{case_id}/consent/otp")
def request_assisted_consent_otp(
    case_id: UUID,
    body: ConsentOtpRequest,
    principal: Principal = Depends(require_any_role("agent", "local-admin")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    if case.consent_channel != "assisted":
        raise HTTPException(status_code=409, detail="Ce dossier attend un accord sur l’espace citoyen")

    identity_link = db.scalar(select(CitizenIdentityLink).where(CitizenIdentityLink.subject_ref == case.subject_ref))
    if identity_link is None or not re.fullmatch(r"\+[1-9][0-9]{7,14}", identity_link.phone_number):
        raise HTTPException(status_code=422, detail="Aucun numéro international n’est rattaché au citoyen")

    now = datetime.now(timezone.utc)
    latest_consent = db.scalar(
        select(Consent).where(Consent.case_id == case.id).order_by(Consent.created_at.desc())
    )
    if latest_consent and latest_consent.status == "granted" and (
        latest_consent.expires_at is None or _utc(latest_consent.expires_at) > now
    ):
        raise HTTPException(status_code=409, detail="Un accord valide existe déjà pour ce dossier")

    scope, scope_digest = _consent_scope(db, case)
    if not scope:
        raise HTTPException(status_code=409, detail="Aucune vérification n’est associée à cette démarche")

    active_challenge = db.scalar(
        select(ConsentOtpChallenge)
        .where(
            ConsentOtpChallenge.case_id == case.id,
            ConsentOtpChallenge.requested_by_sub == principal.subject,
            ConsentOtpChallenge.delivery_status.in_({"sent", "simulated"}),
            ConsentOtpChallenge.consumed_at.is_(None),
        )
        .order_by(ConsentOtpChallenge.created_at.desc())
    )
    if active_challenge and _utc(active_challenge.expires_at) > now:
        if not body.resend:
            return _serialize_consent_challenge(active_challenge, identity_link.phone_number)
        if _utc(active_challenge.resend_after) > now:
            raise HTTPException(status_code=429, detail="Attendez avant de renvoyer un code")
    if active_challenge:
        active_challenge.delivery_status = "consumed"
        active_challenge.consumed_at = now

    send_count = db.scalar(select(func.count(ConsentOtpChallenge.id)).where(
        ConsentOtpChallenge.case_id == case.id,
        ConsentOtpChallenge.created_at >= now - timedelta(hours=1),
    )) or 0
    if send_count >= CONSENT_OTP_MAX_SENDS_PER_HOUR:
        raise HTTPException(status_code=429, detail="La limite d’envoi de codes pour ce dossier est atteinte")

    expires_at = now + CONSENT_OTP_TTL
    resend_after = now + CONSENT_OTP_RESEND_DELAY
    try:
        mode = otp_delivery_mode()
    except OtpSimulationConfigurationError as error:
        raise HTTPException(status_code=503, detail="La simulation OTP n’est pas configurée correctement") from error
    challenge_id = uuid4()
    provider_pin_id = None
    code_digest = None
    if mode == "simulated":
        code_digest = simulated_otp_digest(
            challenge_id, "consent", simulated_otp_code(challenge_id, "consent")
        )
    else:
        try:
            otp_provider = InfobipOtpProvider.from_environment()
            if _normalize_burkina_phone(otp_provider.settings.test_phone_number) != identity_link.phone_number:
                raise HTTPException(
                    status_code=409,
                    detail="Le numéro de test Infobip ne correspond pas au numéro du citoyen; aucun code n’a été envoyé.",
                )
            result = otp_provider.send_pin("consent", identity_link.phone_number)
            provider_pin_id = result.pin_id
        except (SmsConfigurationError, SmsDeliveryError) as error:
            logger.warning("Consent OTP SMS failed: %s", getattr(error, "safe_code", str(error)))
            raise HTTPException(status_code=502, detail="Échec de l’envoi du code de consentement par SMS") from error

    challenge = ConsentOtpChallenge(
        id=challenge_id,
        case_id=case.id,
        requested_by_sub=principal.subject,
        provider_pin_id=provider_pin_id,
        code_digest=code_digest,
        scope_digest=scope_digest,
        attempt_count=0,
        delivery_status="simulated" if mode == "simulated" else "sent",
        expires_at=expires_at,
        resend_after=resend_after,
    )
    db.add(challenge)
    _add_event(
        db,
        case,
        "consent_otp_simulated" if mode == "simulated" else "consent_otp_sent",
        "code OTP simulé pour le recueil assisté; aucun SMS envoyé" if mode == "simulated"
        else "code SMS demandé pour le recueil assisté du consentement",
        outcome="simulated" if mode == "simulated" else "sent",
        actor_type="agent",
        actor_ref=principal.subject,
    )
    db.commit()
    db.refresh(challenge)
    return _serialize_consent_challenge(challenge, identity_link.phone_number)


@router.post("/cases/{case_id}/consent/request")
def change_consent_channel(
    case_id: UUID,
    body: ConsentChannelChange,
    principal: Principal = Depends(require_any_role("agent", "local-admin")),
    db: Session = Depends(get_db),
):
    """Switch a pending case between portal consent and assisted consent."""
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    if case.status in {"completed", "rejected", "cancelled"}:
        raise HTTPException(status_code=409, detail="Le parcours de consentement est clôturé pour ce dossier")

    latest_consent = db.scalar(
        select(Consent).where(Consent.case_id == case.id).order_by(Consent.created_at.desc())
    )
    if latest_consent and latest_consent.status == "granted" and (
        latest_consent.expires_at is None or _utc(latest_consent.expires_at) > datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=409, detail="Un consentement actif existe déjà pour ce dossier")

    if body.consent_channel == case.consent_channel:
        return _serialize_case(db, case)

    now = datetime.now(timezone.utc)
    active_challenges = db.scalars(
        select(ConsentOtpChallenge).where(
            ConsentOtpChallenge.case_id == case.id,
            ConsentOtpChallenge.consumed_at.is_(None),
            ConsentOtpChallenge.delivery_status.in_({"sent", "simulated"}),
        )
    ).all()
    for challenge in active_challenges:
        challenge.delivery_status = "expired"
        challenge.consumed_at = now

    case.consent_channel = body.consent_channel
    db.add(Notification(
        case_id=case.id,
        recipient_ref=case.subject_ref,
        channel="platform",
        title="Consentement requis",
        message=(
            "Une demande de consentement vous attend sur la plateforme. "
            "Connectez-vous pour consulter les vérifications prévues et répondre."
        ),
        delivery_status="delivered",
    ))

    sms_notification = None
    if body.consent_channel == "web":
        procedure = db.get(Procedure, case.procedure_id)
        message = render_consent_request(procedure.title if procedure else None, case.id.hex[:8].upper())
        provider_name = os.getenv("SMS_PROVIDER", "simulated").lower()
        if message is None:
            delivery_status = "failed"
            delivery_error = "sms_template_missing_data"
        else:
            delivery_status = "queued" if provider_name == "infobip" else "simulated"
            delivery_error = None
        sms_notification = Notification(
            case_id=case.id,
            recipient_ref=case.subject_ref,
            channel="sms",
            title="Consentement requis",
            message=message or "",
            delivery_status=delivery_status,
            delivery_error=delivery_error,
        )
        db.add(sms_notification)

    _add_event(
        db,
        case,
        "consent_requested",
        "mode de recueil du consentement modifié",
        outcome=body.consent_channel,
        actor_type="agent",
        actor_ref=principal.subject,
    )
    db.commit()
    if sms_notification and sms_notification.delivery_status == "queued":
        dispatch_sms_notification(db, sms_notification)
    db.refresh(case)
    return _serialize_case(db, case)


@router.post("/cases/{case_id}/consent/otp/verify")
def verify_assisted_consent_otp(
    case_id: UUID,
    body: ConsentOtpVerify,
    principal: Principal = Depends(require_any_role("agent", "local-admin")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    challenge = db.scalar(
        select(ConsentOtpChallenge)
        .where(
            ConsentOtpChallenge.case_id == case.id,
            ConsentOtpChallenge.requested_by_sub == principal.subject,
            ConsentOtpChallenge.delivery_status.in_({"sent", "simulated"}),
            ConsentOtpChallenge.consumed_at.is_(None),
        )
        .order_by(ConsentOtpChallenge.created_at.desc())
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Aucun code actif pour ce dossier")

    now = datetime.now(timezone.utc)
    if _utc(challenge.expires_at) <= now or challenge.attempt_count >= CONSENT_OTP_MAX_ATTEMPTS:
        challenge.delivery_status = "expired"
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=410, detail="Le code a expiré. Demandez-en un nouveau.")

    _, current_scope_digest = _consent_scope(db, case)
    if current_scope_digest != challenge.scope_digest:
        challenge.delivery_status = "expired"
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=409, detail="Le périmètre des vérifications a changé. Demandez un nouveau code.")

    try:
        if challenge.code_digest is not None:
            verified = simulated_otp_matches(challenge.id, "consent", body.code, challenge.code_digest)
        elif challenge.provider_pin_id:
            verified = InfobipOtpProvider.from_environment().verify_pin(challenge.provider_pin_id, body.code)
        else:
            raise HTTPException(status_code=409, detail="Le défi OTP ne peut pas être vérifié")
    except OtpSimulationConfigurationError as error:
        raise HTTPException(status_code=503, detail="La configuration du code de démonstration est absente") from error
    except (SmsConfigurationError, SmsDeliveryError) as error:
        logger.warning("Consent OTP verification failed: %s", getattr(error, "safe_code", str(error)))
        raise HTTPException(status_code=502, detail="La vérification du code par Infobip a échoué") from error
    if not verified:
        challenge.attempt_count += 1
        if challenge.attempt_count >= CONSENT_OTP_MAX_ATTEMPTS:
            challenge.delivery_status = "expired"
            challenge.consumed_at = now
        _add_event(
            db,
            case,
            "consent_otp_rejected",
            "code de consentement assisté invalide",
            outcome="invalid_code",
            actor_type="agent",
            actor_ref=principal.subject,
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Code incorrect")

    scope, _ = _consent_scope(db, case)
    links = {link.question_id for link, _ in scope}
    procedure = db.get(Procedure, case.procedure_id)
    consent_days = procedure.consent_days if procedure else 30
    previous_grants = db.scalars(select(Consent).where(
        Consent.case_id == case.id,
        Consent.status == "granted",
    )).all()
    for previous in previous_grants:
        previous.status = "revoked"
        previous.revoked_at = now

    simulated_verification = challenge.code_digest is not None
    consent = Consent(
        case_id=case.id,
        subject_ref=case.subject_ref,
        status="granted",
        granted_at=now,
        expires_at=now + timedelta(days=consent_days),
        notice_version="consent-assisted-v1",
        channel="assisted",
        evidence_ref=f"consent-otp-simulated:{challenge.id}" if simulated_verification
        else f"consent-otp:{challenge.id}",
        created_at=now,
    )
    db.add(consent)
    db.flush()
    for question_id in links:
        db.add(ConsentQuestion(consent_id=consent.id, question_id=question_id))
    challenge.delivery_status = "consumed"
    challenge.consumed_at = now
    challenge.code_digest = None
    challenge.provider_pin_id = None
    _add_event(
        db,
        case,
        "consent_recorded",
        "consentement saisi après validation OTP simulée; aucun téléphone vérifié"
        if simulated_verification else "consentement confirmé par code à usage unique reçu par SMS",
        outcome="granted",
        actor_type="citizen",
        actor_ref=case.subject_ref,
    )
    db.commit()
    db.refresh(consent)
    return {
        "id": str(consent.id),
        "case_id": str(case.id),
        "status": consent.status,
        "channel": consent.channel,
        "question_codes": [question.code for _, question in scope],
        "granted_at": consent.granted_at,
        "expires_at": consent.expires_at,
    }


@router.get("/cases/{case_id}")
def get_case(
    case_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    return _serialize_case(db, case)


@router.get("/notifications")
def list_notifications(
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    if not principal.citizen_ref:
        raise HTTPException(status_code=403, detail="Jeton citoyen sans référence citoyen")
    notifications = db.scalars(
        select(Notification)
        .where(
            Notification.recipient_ref == principal.citizen_ref,
            Notification.channel == "platform",
        )
        .order_by(Notification.created_at.desc())
    ).all()
    return [
        {
            "id": str(notification.id),
            "case_id": str(notification.case_id),
            "caseId": str(notification.case_id),
            "title": notification.title,
            "message": notification.message,
            "created_at": notification.created_at,
            "createdAt": notification.created_at,
            "read_at": notification.read_at,
            "readAt": notification.read_at,
        }
        for notification in notifications
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    if not principal.citizen_ref:
        raise HTTPException(status_code=403, detail="Jeton citoyen sans référence citoyen")
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_ref == principal.citizen_ref,
            Notification.channel == "platform",
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
    return {"id": str(notification.id), "read_at": notification.read_at, "readAt": notification.read_at}


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
    if body.channel != case.consent_channel:
        raise HTTPException(status_code=409, detail="Le canal ne correspond plus au parcours de consentement du dossier")
    if case.consent_channel == "assisted" and body.decision == "granted":
        raise HTTPException(
            status_code=409,
            detail="Ce dossier attend le code SMS du parcours assisté; le consentement direct sur le portail est désactivé.",
        )
    links = db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == case.procedure_id)).all()
    allowed = {db.get(Question, link.question_id).code: link.question_id for link in links}
    if len(set(body.question_codes)) != len(body.question_codes) or not set(body.question_codes) <= allowed.keys():
        raise HTTPException(status_code=422, detail="Une ou plusieurs questions ne font pas partie de la démarche")
    now = datetime.now(timezone.utc)
    procedure = db.get(Procedure, case.procedure_id)
    consent_days = procedure.consent_days if procedure else 30
    expires_at = body.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise HTTPException(status_code=422, detail="La date d’expiration doit inclure un fuseau horaire")
        if expires_at <= now or expires_at > now + timedelta(days=consent_days):
            raise HTTPException(status_code=422, detail=f"Le consentement doit expirer dans les {consent_days} prochains jours")
    else:
        expires_at = now + timedelta(days=consent_days)

    previous_grants = db.scalars(select(Consent).where(
        Consent.case_id == case.id, Consent.status == "granted"
    )).all()
    for previous in previous_grants:
        previous.status = "revoked"
        previous.revoked_at = now

    consent = Consent(case_id=case.id, subject_ref=case.subject_ref, status=body.decision,
                      granted_at=now if body.decision == "granted" else None,
                      expires_at=expires_at, notice_version=body.notice_version, channel=body.channel,
                      created_at=now)
    db.add(consent)
    db.flush()
    for code in body.question_codes:
        db.add(ConsentQuestion(consent_id=consent.id, question_id=allowed[code]))
    _add_event(db, case, "consent_recorded", "consentement pour la démarche",
               outcome=body.decision, actor_type="citizen", actor_ref=case.subject_ref)
    db.commit()
    db.refresh(consent)
    return {"id": str(consent.id), "case_id": str(case.id), "caseId": str(case.id), "status": consent.status,
            "question_codes": body.question_codes, "notice_version": consent.notice_version,
            "channel": consent.channel, "granted_at": consent.granted_at,
            "questionCodes": body.question_codes, "noticeVersion": consent.notice_version,
            "grantedAt": consent.granted_at, "revoked_at": consent.revoked_at,
            "expires_at": consent.expires_at, "expiresAt": consent.expires_at}


@router.delete("/cases/{case_id}/consent")
def revoke_consent(
    case_id: UUID,
    principal: Principal = Depends(require_role("citizen")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    if principal.citizen_ref != case.subject_ref:
        raise HTTPException(status_code=403, detail="Seul le citoyen concerné peut révoquer son consentement")
    consent = db.scalar(select(Consent).where(Consent.case_id == case.id)
                        .order_by(Consent.created_at.desc()))
    if (consent is None or consent.status != "granted" or
            (consent.expires_at is not None and consent.expires_at <= datetime.now(timezone.utc))):
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
    principal: Principal = Depends(require_any_role("agent", "local-admin")),
    db: Session = Depends(get_db),
):
    case = _case_or_404(db, case_id)
    _authorize_case_access(case, db, principal)
    now = datetime.now(timezone.utc)
    consent = db.scalar(select(Consent).where(Consent.case_id == case.id)
                        .order_by(Consent.created_at.desc()))
    requests = db.scalars(select(RegistryRequest).where(RegistryRequest.case_id == case.id)).all()
    links = {link.question_id: link for link in db.scalars(
        select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == case.procedure_id)).all()}
    consent_ids = set()
    if (consent and consent.status == "granted" and
            (consent.expires_at is None or consent.expires_at > now)):
        consent_ids = set(db.scalars(select(ConsentQuestion.question_id).where(ConsentQuestion.consent_id == consent.id)).all())
    if consent is None or not consent_ids:
        _add_event(db, case, "checks_blocked", "consentement absent ou expiré", outcome="blocked")
        if case.status in {"received", "in_progress", "pending"}:
            case.status = "pending"
        db.commit()
        raise HTTPException(status_code=403, detail="Consentement citoyen actif requis")

    from connectors import build_connector

    connector = build_connector()
    stale_request_before = now - timedelta(seconds=REQUEST_LEASE_SECONDS)
    for request in requests:
        if request.status in {"confirmed", "rejected", "not_found", "ambiguous"}:
            continue
        question = db.get(Question, request.question_id)
        link = links[question.id]
        permission = db.scalar(select(Permission).where(
            Permission.requester_administration_id == case.requester_administration_id,
            Permission.question_id == question.id,
            Permission.active.is_(True),
            Permission.status == "approved",
            (Permission.valid_from.is_(None) | (Permission.valid_from <= now)),
            (Permission.valid_until.is_(None) | (Permission.valid_until > now)),
        ))
        if not question.active or permission is None or question.id not in consent_ids:
            request.status = "blocked"
            _add_event(db, case, "check_blocked", "consentement ou autorisation absent", outcome="blocked", question=question)
            continue
        if not request.lookup_identifier_ciphertext and case.subject_ref.startswith("CITIZEN:"):
            identifier_type = QUESTION_IDENTIFIER_TYPES.get(question.code)
            if identifier_type:
                saved_identifier = db.scalar(select(CitizenDocumentIdentifier).where(
                    CitizenDocumentIdentifier.subject_ref == case.subject_ref,
                    CitizenDocumentIdentifier.identifier_type == identifier_type,
                ))
                if saved_identifier is not None:
                    request.lookup_identifier_type = identifier_type
                    request.lookup_identifier_ciphertext = saved_identifier.identifier_ciphertext
        registry_info = _check_payload(db, request)
        if not request.lookup_identifier_ciphertext and not case.subject_ref.startswith("ACTE:"):
            request.status = "blocked"
            _add_event(db, case, "check_blocked", "identifiant de registre absent", outcome="missing_identifier",
                       actor_type="system", question=question, registry=registry_info["registry"],
                       categories=[question.code])
            db.commit()
            continue

        # Claim the logical request atomically so concurrent calls cannot query
        # the same registry twice. A stale pending claim can be recovered later.
        claim = db.execute(
            update(RegistryRequest)
            .where(
                RegistryRequest.id == request.id,
                or_(
                    RegistryRequest.status.in_({"queued", "unavailable", "error", "blocked"}),
                    and_(
                        RegistryRequest.status == "pending",
                        or_(
                            RegistryRequest.updated_at.is_(None),
                            RegistryRequest.updated_at < stale_request_before,
                        ),
                    ),
                ),
            )
            .values(
                status="pending",
                attempt_count=RegistryRequest.attempt_count + 1,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if claim.rowcount != 1:
            db.refresh(request)
            continue

        previous_attempt_number = request.attempt_count
        if request.status == "pending":
            abandoned_attempt = db.scalar(select(RequestAttempt).where(
                RequestAttempt.registry_request_id == request.id,
                RequestAttempt.attempt_number == previous_attempt_number,
                RequestAttempt.status == "started",
            ))
            if abandoned_attempt is not None:
                abandoned_attempt.status = "failed"
                abandoned_attempt.finished_at = now
                abandoned_attempt.error_code = "attempt_lease_expired"

        request.status = "pending"
        request.attempt_count += 1
        attempt = RequestAttempt(registry_request_id=request.id, attempt_number=request.attempt_count, status="started")
        db.add(attempt)
        db.commit()
        try:
            reply = connector.query(registry_info["organization"], question.service_code, registry_info["payload"])
        except Exception:
            reply = {"status": "unavailable", "data": None, "message": "Registre indisponible", "transport_id": None}
        transport_status = reply.get("status")
        data = reply.get("data") if transport_status == "ok" else None
        value = data.get(question.response_key) if isinstance(data, dict) else None
        valid_boolean = type(value) is bool
        valid_pivot = question.response_key == "pivot_id" and type(value) is str and value == case.subject_ref
        valid_document_found = (
            request.lookup_identifier_ciphertext
            and question.response_key == "found"
            and value is True
        )
        if transport_status == "ok" and (valid_boolean or valid_pivot or valid_document_found):
            request.status = "confirmed" if value is True or valid_pivot else "rejected"
            request.minimal_result = {question.response_key: value}
            attempt.status = "succeeded"
        else:
            mapping = {"not_found": "not_found", "ambiguous": "ambiguous", "refused": "blocked",
                       "unavailable": "unavailable", "invalid_request": "error"}
            request.status = mapping.get(transport_status, "error") if transport_status != "ok" else "error"
            request.minimal_result = None
            attempt.status = "failed"
            attempt.error_code = "invalid_response" if transport_status == "ok" else transport_status or "invalid_response"
        if request.status in {"confirmed", "rejected", "not_found", "ambiguous"}:
            request.lookup_identifier_type = None
            request.lookup_identifier_ciphertext = None
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
