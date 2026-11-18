"""Inscription, recherche et vérification des événements."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Engine, or_, select, text
from sqlalchemy.orm import sessionmaker

from .chain import as_utc, event_hash
from .models import Base, JournalEvent
from .schemas import ChainReport, EventIn

# Verrou PostgreSQL qui sérialise les ajouts : une seule chaîne pour tout le journal,
# même avec plusieurs processus. Le verrou du processus suffit pour SQLite (tests).
CHAIN_LOCK_KEY = 0x4A4F55524E414C
TEXT_COLUMNS = (JournalEvent.event_type, JournalEvent.purpose, JournalEvent.actor_ref, JournalEvent.outcome)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class JournalStore:
    def __init__(self, engine: Engine, clock: Callable[[], datetime] = utc_now) -> None:
        self._engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False)
        self._clock = clock
        self._lock = threading.Lock()

    def create_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def append(self, body: EventIn, *, source: str) -> JournalEvent:
        with self._lock, self._sessions.begin() as session:
            if session.get_bind().dialect.name == "postgresql":
                session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": CHAIN_LOCK_KEY})
            last = session.scalar(select(JournalEvent).order_by(JournalEvent.sequence.desc()).limit(1))
            event = JournalEvent(
                id=uuid4(),
                sequence=last.sequence + 1 if last else 1,
                occurred_at=as_utc(self._clock()),
                source=source,
                previous_hash=last.event_hash if last else None,
                **body.model_dump(),
            )
            event.event_hash = event_hash(event)
            session.add(event)
        return event

    def get(self, event_id: UUID) -> JournalEvent | None:
        with self._sessions() as session:
            return session.get(JournalEvent, event_id)

    def search(
        self,
        *,
        subject_ref: str | None = None,
        case_id: str | None = None,
        correlation_id: str | None = None,
        event_types: Sequence[str] = (),
        requester_code: str | None = None,
        actor_type: str | None = None,
        text_query: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        after: int | None = None,
        descending: bool = False,
        limit: int = 100,
    ) -> tuple[list[JournalEvent], int | None]:
        query = select(JournalEvent)
        for column, value in (
            (JournalEvent.subject_ref, subject_ref),
            (JournalEvent.case_id, case_id),
            (JournalEvent.correlation_id, correlation_id),
            (JournalEvent.requester_code, requester_code),
            (JournalEvent.actor_type, actor_type),
        ):
            if value is not None:
                query = query.where(column == value)
        if event_types:
            query = query.where(JournalEvent.event_type.in_(list(event_types)))
        if text_query and text_query.strip():
            pattern = _like(text_query.strip())
            query = query.where(or_(*(column.ilike(pattern, escape="\\") for column in TEXT_COLUMNS)))
        if occurred_from is not None:
            query = query.where(JournalEvent.occurred_at >= as_utc(occurred_from))
        if occurred_to is not None:
            query = query.where(JournalEvent.occurred_at < as_utc(occurred_to))
        if after is not None:
            query = query.where(JournalEvent.sequence < after if descending else JournalEvent.sequence > after)
        order = JournalEvent.sequence.desc() if descending else JournalEvent.sequence
        with self._sessions() as session:
            rows = list(session.scalars(query.order_by(order).limit(limit + 1)))
        page = rows[:limit]
        return page, page[-1].sequence if len(rows) > limit else None

    def verify(self) -> ChainReport:
        previous: JournalEvent | None = None
        checked = 0
        with self._sessions() as session:
            events = session.scalars(select(JournalEvent).order_by(JournalEvent.sequence).execution_options(yield_per=500))
            for event in events:
                checked += 1
                expected_sequence = previous.sequence + 1 if previous else 1
                expected_previous = previous.event_hash if previous else None
                if (event.sequence != expected_sequence or event.previous_hash != expected_previous
                        or event.event_hash != event_hash(event)):
                    return ChainReport(valid=False, events=checked, first_invalid_sequence=event.sequence, last_hash=None)
                previous = event
        return ChainReport(valid=True, events=checked, first_invalid_sequence=None,
                           last_hash=previous.event_hash if previous else None)
