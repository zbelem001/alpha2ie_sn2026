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
    connector_config_ref: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


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
    __table_args__ = (UniqueConstraint("requester_administration_id", "question_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    requester_administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Procedure(Base):
    __tablename__ = "procedures"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    owner_administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
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


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('received','in_progress','pending','completed','rejected','cancelled')",
            name="ck_cases_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    procedure_id: Mapped[UUID] = mapped_column(ForeignKey("procedures.id", ondelete="RESTRICT"))
    requester_administration_id: Mapped[UUID] = mapped_column(ForeignKey("administrations.id", ondelete="RESTRICT"))
    subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="received")
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
