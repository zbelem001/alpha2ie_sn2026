"""Couche journal de traçabilité : API FastAPI (spécification générée : journal/openapi.yaml).

Pas de `from __future__ import annotations` ici : FastAPI doit lire les dépendances writer/reader,
définies dans create_app, au moment où les routes sont déclarées.
"""

import os
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine, create_engine

from .schemas import ActorType, ChainReport, Event, EventIn, EventPage
from .security import caller_for, parse_tokens
from .store import JournalStore, utc_now

DESCRIPTION = """Retrouver **chaque consultation** : qui a demandé quoi, quand, pour quelle démarche, sur quelle base.

- Écriture : la couche démarches (dossiers, accords, vérifications, signalements) et la couche
  consentement-minimisation (ce qui sort de chez le détenteur, et ce qu'elle refuse).
- Les refus et les pannes y figurent, pas seulement les réponses positives.
- Ajout seul : aucune route ne modifie ni ne supprime ; chaque événement porte l'empreinte du
  précédent (`GET /v1/chain/verify`).
- Aucune valeur issue d'un registre n'y est inscrite : des références, des codes, le résultat.
"""

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(
    auto_error=False, description="Jeton de service de la couche appelante (JOURNAL_WRITE_TOKENS, JOURNAL_READ_TOKENS)"
))]


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/journal")


def _authorize(credentials: HTTPAuthorizationCredentials | None, allowed: Mapping[str, str],
               other: Mapping[str, str], wrong_scope: str) -> str:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton de service requis", headers={"WWW-Authenticate": "Bearer"})
    name = caller_for(credentials.credentials, allowed)
    if name is not None:
        return name
    if caller_for(credentials.credentials, other) is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, wrong_scope)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton de service inconnu", headers={"WWW-Authenticate": "Bearer"})


def create_app(
    *,
    engine: Engine | None = None,
    write_tokens: Mapping[str, str] | None = None,
    read_tokens: Mapping[str, str] | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> FastAPI:
    """Jetons : {jeton: nom de la couche} ; par défaut, JOURNAL_WRITE_TOKENS et JOURNAL_READ_TOKENS."""
    store = JournalStore(engine if engine is not None else create_engine(database_url(), pool_pre_ping=True), clock)
    store.create_schema()
    writers = dict(write_tokens) if write_tokens is not None else parse_tokens(os.environ.get("JOURNAL_WRITE_TOKENS"))
    readers = dict(read_tokens) if read_tokens is not None else parse_tokens(os.environ.get("JOURNAL_READ_TOKENS"))

    def writer(credentials: Credentials) -> str:
        return _authorize(credentials, writers, readers, "Ce jeton ne permet que la lecture du journal")

    def reader(credentials: Credentials) -> str:
        return _authorize(credentials, readers, writers, "Ce jeton ne permet que l'écriture au journal")

    app = FastAPI(title="Couche journal de traçabilité", version="0.1.0", description=DESCRIPTION)
    app.state.store = store

    @app.get("/health", tags=["santé"], summary="État du service")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/events", status_code=status.HTTP_201_CREATED, response_model=Event, tags=["journal"],
              summary="Inscrire un événement",
              responses={401: {"description": "Jeton absent ou inconnu"}, 403: {"description": "Jeton de lecture seule"}})
    def append_event(body: EventIn, source: Annotated[str, Depends(writer)]) -> Event:
        return Event.model_validate(store.append(body, source=source))

    @app.get("/v1/events", response_model=EventPage, tags=["journal"],
             summary="Rechercher des événements : par citoyen, par demande, par date",
             responses={401: {"description": "Jeton absent ou inconnu"}, 403: {"description": "Jeton d'écriture seule"}})
    def search_events(
        _reader: Annotated[str, Depends(reader)],
        subject_ref: Annotated[str | None, Query(max_length=160, description="Citoyen")] = None,
        case_id: Annotated[str | None, Query(max_length=64, description="Demande (dossier)")] = None,
        correlation_id: Annotated[str | None, Query(max_length=160, description="Consultation (identifiant de requête)")] = None,
        event_type: Annotated[list[str] | None, Query(description="Type(s) d'événement, répétable")] = None,
        requester_code: Annotated[str | None, Query(max_length=160, description="Administration demandeuse")] = None,
        actor_type: Annotated[ActorType | None, Query(description="Qui agit")] = None,
        q: Annotated[str | None, Query(max_length=100, description="Texte cherché dans le type, la finalité, l'acteur et le résultat")] = None,
        occurred_from: Annotated[datetime | None, Query(alias="from", description="Depuis (inclus), ISO 8601")] = None,
        occurred_to: Annotated[datetime | None, Query(alias="to", description="Jusqu'à (exclu), ISO 8601")] = None,
        after: Annotated[int | None, Query(ge=0, description="Curseur : next_after de la page précédente")] = None,
        order: Annotated[Literal["asc", "desc"], Query(description="Ordre d'inscription")] = "asc",
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> EventPage:
        rows, next_after = store.search(
            subject_ref=subject_ref, case_id=case_id, correlation_id=correlation_id, event_types=event_type or (),
            requester_code=requester_code, actor_type=actor_type, text_query=q, occurred_from=occurred_from,
            occurred_to=occurred_to, after=after, descending=order == "desc", limit=limit,
        )
        return EventPage(events=[Event.model_validate(row) for row in rows], next_after=next_after)

    @app.get("/v1/events/{event_id}", response_model=Event, tags=["journal"], summary="Lire un événement",
             responses={404: {"description": "Événement introuvable"}})
    def get_event(event_id: UUID, _reader: Annotated[str, Depends(reader)]) -> Event:
        event = store.get(event_id)
        if event is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Événement introuvable")
        return Event.model_validate(event)

    @app.get("/v1/chain/verify", response_model=ChainReport, tags=["journal"],
             summary="Vérifier la chaîne d'empreintes de tout le journal")
    def verify_chain(_reader: Annotated[str, Depends(reader)]) -> ChainReport:
        return store.verify()

    return app
