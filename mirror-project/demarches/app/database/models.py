from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

JSON_VALUE = JSON().with_variant(JSONB, "postgresql")


class Administration(Base):
    __tablename__ = "administrations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Registry(Base):
    __tablename__ = "registries"
    __table_args__ = (UniqueConstraint("administration_id", "code"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="Registre")
    base_url: Mapped[str | None] = mapped_column(String(500))
    connector_config_ref: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_test_success: Mapped[bool | None] = mapped_column(Boolean)


class RegistryService(Base):
    __tablename__ = "registry_services"
    __table_args__ = (UniqueConstraint("registry_id", "code", name="uq_registry_services_registry_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    registry_id: Mapped[UUID] = mapped_column(ForeignKey("registries.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    registry_id: Mapped[UUID] = mapped_column(ForeignKey("registries.id", ondelete="RESTRICT"))
    service_code: Mapped[str] = mapped_column(String(100), nullable=False)
    response_key: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("requester_administration_id", "question_id"),
        CheckConstraint("status IN ('approved','requested','suspended','not_requested')", name="ck_permissions_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    requester_administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_requested")
    purpose: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Procedure(Base):
    __tablename__ = "procedures"
    __table_args__ = (CheckConstraint("consent_days BETWEEN 1 AND 30", name="ck_procedures_consent_days"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    owner_administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    consent_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ProcedureQuestion(Base):
    __tablename__ = "procedure_questions"
    __table_args__ = (
        UniqueConstraint("procedure_id", "question_id"),
        CheckConstraint("position >= 0", name="ck_procedure_questions_position"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    procedure_id: Mapped[UUID] = mapped_column(ForeignKey("procedures.id", ondelete="CASCADE"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(40))
    document_label: Mapped[str | None] = mapped_column(String(160))
    document_hint: Mapped[str | None] = mapped_column(String(300))


class AdministrationAuditEvent(Base):
    __tablename__ = "administration_audit_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"), index=True)
    actor_sub: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(40), nullable=False, default="local-admin")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('received','in_progress','pending','completed','rejected','cancelled')",
            name="ck_cases_status",
        ),
        CheckConstraint("consent_channel IN ('assisted','web')", name="ck_cases_consent_channel"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    procedure_id: Mapped[UUID] = mapped_column(ForeignKey("procedures.id", ondelete="RESTRICT"))
    requester_administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    applicant_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Citoyen", server_default="Citoyen")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="received")
    consent_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="web", server_default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint("status IN ('granted','refused','revoked','expired')", name="ck_consents_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="RESTRICT"), index=True)
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notice_version: Mapped[str] = mapped_column(String(60), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentQuestion(Base):
    __tablename__ = "consent_questions"
    __table_args__ = (UniqueConstraint("consent_id", "question_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    consent_id: Mapped[UUID] = mapped_column(ForeignKey("consents.id", ondelete="CASCADE"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))


class ConsentOtpChallenge(Base):
    """Short-lived provider OTP or explicitly simulated demo challenge."""
    __tablename__ = "consent_otp_challenges"
    __table_args__ = (
        CheckConstraint("attempt_count BETWEEN 0 AND 5", name="ck_consent_otp_attempts"),
        CheckConstraint("delivery_status IN ('sent','simulated','failed','consumed','expired')", name="ck_consent_otp_delivery_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="RESTRICT"), index=True)
    requested_by_sub: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_pin_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    code_digest: Mapped[str | None] = mapped_column(String(64))
    scope_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resend_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegistrationOtpChallenge(Base):
    """Phone verification challenge used before the first citizen registration."""
    __tablename__ = "registration_otp_challenges"
    __table_args__ = (
        CheckConstraint("attempt_count BETWEEN 0 AND 5", name="ck_registration_otp_attempts"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    provider_pin_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    code_digest: Mapped[str | None] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resend_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegistryRequest(Base):
    __tablename__ = "registry_requests"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        CheckConstraint(
            "status IN ('queued','pending','confirmed','rejected','ambiguous','not_found','unavailable','blocked','error')",
            name="ck_registry_requests_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="RESTRICT"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimal_result: Mapped[dict | None] = mapped_column(JSON_VALUE)
    lookup_identifier_type: Mapped[str | None] = mapped_column(String(80))
    lookup_identifier_ciphertext: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RequestAttempt(Base):
    __tablename__ = "request_attempts"
    __table_args__ = (
        UniqueConstraint("registry_request_id", "attempt_number"),
        CheckConstraint("attempt_number > 0", name="ck_attempts_number_positive"),
        CheckConstraint("status IN ('started','succeeded','failed')", name="ck_attempts_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    registry_request_id: Mapped[UUID] = mapped_column(ForeignKey("registry_requests.id", ondelete="RESTRICT"))
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transport_id: Mapped[str | None] = mapped_column(String(200))
    error_code: Mapped[str | None] = mapped_column(String(80))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('citizen','agent','administration','system')",
            name="ck_audit_events_actor_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="RESTRICT"), index=True)
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(160))
    requester_administration_id: Mapped[UUID | None] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    registry_id: Mapped[UUID | None] = mapped_column(ForeignKey("registries.id", ondelete="RESTRICT"))
    question_id: Mapped[UUID | None] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(40))
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    data_categories: Mapped[list | None] = mapped_column(JSON_VALUE)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(160))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str | None] = mapped_column(String(64))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("channel IN ('platform','sms')", name="ck_notifications_channel"),
        CheckConstraint(
            "delivery_status IN ('queued','sent','delivered','simulated','failed')",
            name="ck_notifications_delivery_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="RESTRICT"), index=True)
    recipient_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(80))
    delivery_error: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CitizenIdentityLink(Base):
    """Mapping from a Keycloak account and verified phone to an internal citizen pivot."""
    __tablename__ = "citizen_identity_links"
    __table_args__ = (
        UniqueConstraint("principal_sub", name="uq_citizen_identity_links_principal_sub"),
        UniqueConstraint("subject_ref", name="uq_citizen_identity_links_subject_ref"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    principal_sub: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(24), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CitizenDocumentIdentifier(Base):
    """Encrypted identifier supplied by the citizen for a specific source registry."""
    __tablename__ = "citizen_document_identifiers"
    __table_args__ = (
        UniqueConstraint("principal_sub", "identifier_type", name="uq_citizen_identifier_account_type"),
        UniqueConstraint("identifier_digest", name="uq_citizen_identifier_digest"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    principal_sub: Mapped[str] = mapped_column(
        ForeignKey("citizen_identity_links.principal_sub", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(80), nullable=False)
    registry_code: Mapped[str] = mapped_column(String(120), nullable=False)
    identifier_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    identifier_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
