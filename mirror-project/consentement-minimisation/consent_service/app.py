"""Couche consentement et minimisation : API FastAPI (spécification générée : openapi.yaml).

Pas de `from __future__ import annotations` ici : FastAPI doit lire la dépendance `caller`,
définie dans create_app, au moment où les routes sont déclarées.
"""

import os
from collections.abc import Callable, Mapping
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from journal_client import JournalUnavailable, journal_from_env
from sqlalchemy import Engine, create_engine

from .consents import ConsentError, ConsentStore, utc_now
from .guard import HolderGuard
from .holders import Holder, load_holders, reference_date
from .schemas import Consent, ConsentIn, Envelope, HolderView, RuleView
from .security import caller_for, parse_tokens

DESCRIPTION = """Rien ne sort de chez un détenteur sans l'accord du citoyen, et rien que l'utile (« majeur : oui »).

- **Registre des accords** (`/v1/consents`, jeton de service de la couche démarches) : chaque
  décision du citoyen pour un dossier, son périmètre exact (question, détenteur, service), sa
  fin de validité, son retrait. Chaque décision et chaque retrait sont inscrits au journal.
- **Garde** (`/holders/{détenteur}/services/{service}`), placée devant chaque registre et appelée
  par la passerelle : même contrat que les registres. Elle vérifie l'accord désigné par
  `X-Consent-Id` (demandeur `X-Road-Client`, démarche, personne, service), appelle le registre,
  réduit sa réponse selon la règle du service (`GET /holders`), inscrit la réponse ou le refus au
  journal, puis répond. Elle fonctionne devant n'importe quel registre qui respecte le contrat.
"""

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(
    auto_error=False, description="Jeton de service de la couche démarches (CONSENT_TOKENS)"
))]


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/consentement")


def _holder_view(holder: Holder) -> HolderView:
    return HolderView(slug=holder.slug, organization=holder.organization, name=holder.name, services=[
        RuleView(service=rule.service, basis=rule.basis, procedures=list(rule.procedures),
                 registry_service=rule.called_service, transmits=rule.transmits())
        for rule in holder.services.values()
    ])


def create_app(
    *,
    engine: Engine | None = None,
    journal: Any = None,
    tokens: Mapping[str, str] | None = None,
    holders: Mapping[str, Holder] | None = None,
    registry_clients: Mapping[str, httpx.Client] | None = None,
    clock: Callable[[], datetime] = utc_now,
    today: Callable[[], date] = reference_date,
) -> FastAPI:
    """Par défaut, configuration par l'environnement (README) ; les tests injectent chaque élément."""
    journal = journal if journal is not None else journal_from_env()
    store = ConsentStore(engine if engine is not None else create_engine(database_url(), pool_pre_ping=True),
                         journal, clock)
    store.create_schema()
    callers = dict(tokens) if tokens is not None else parse_tokens(os.environ.get("CONSENT_TOKENS"))
    guard = HolderGuard(holders if holders is not None else load_holders(), store, journal,
                        clients=registry_clients, timeout=float(os.environ.get("REGISTRY_TIMEOUT_S") or 3),
                        today=today)

    def caller(credentials: Credentials) -> str:
        name = caller_for(credentials.credentials, callers) if credentials else None
        if name is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton de service requis",
                                headers={"WWW-Authenticate": "Bearer"})
        return name

    def failure(error: Exception) -> HTTPException:
        if isinstance(error, ConsentError):
            return HTTPException(error.status_code, error.detail)
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                             "Journal de traçabilité indisponible : rien n'est enregistré")

    app = FastAPI(title="Couche consentement et minimisation", version="0.1.0", description=DESCRIPTION)
    app.state.store, app.state.guard = store, guard

    @app.get("/health", tags=["santé"], summary="État du service")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- Registre des accords (côté demandeur) ----------------------------------------------

    @app.post("/v1/consents", status_code=status.HTTP_201_CREATED, response_model=Consent, tags=["accords"],
              summary="Enregistrer la décision du citoyen pour un dossier",
              responses={401: {"description": "Jeton absent ou inconnu"}, 503: {"description": "Journal indisponible"}})
    def record_consent(body: ConsentIn, _caller: Annotated[str, Depends(caller)]) -> Consent:
        try:
            return store.record(body)
        except (ConsentError, JournalUnavailable) as error:
            raise failure(error) from error

    @app.get("/v1/consents", response_model=list[Consent], tags=["accords"],
             summary="Accords d'un dossier ou d'un citoyen, du plus récent au plus ancien")
    def list_consents(
        _caller: Annotated[str, Depends(caller)],
        case_id: Annotated[str | None, Query(max_length=64, description="Dossier")] = None,
        subject_ref: Annotated[str | None, Query(max_length=160, description="Citoyen")] = None,
        active: Annotated[bool | None, Query(description="Seulement les accords actifs (true) ou inactifs (false)")] = None,
    ) -> list[Consent]:
        if case_id is None and subject_ref is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Préciser case_id ou subject_ref")
        return store.search(case_id=case_id, subject_ref=subject_ref, active=active)

    @app.get("/v1/consents/{consent_id}", response_model=Consent, tags=["accords"], summary="Lire un accord",
             responses={404: {"description": "Accord introuvable"}})
    def get_consent(consent_id: UUID, _caller: Annotated[str, Depends(caller)]) -> Consent:
        consent = store.get(consent_id)
        if consent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Accord introuvable")
        return consent

    @app.post("/v1/consents/{consent_id}/revoke", response_model=Consent, tags=["accords"],
              summary="Retirer un accord actif",
              responses={404: {"description": "Accord introuvable"}, 409: {"description": "Aucun accord actif"},
                         503: {"description": "Journal indisponible"}})
    def revoke_consent(consent_id: UUID, _caller: Annotated[str, Depends(caller)]) -> Consent:
        try:
            return store.revoke(consent_id)
        except (ConsentError, JournalUnavailable) as error:
            raise failure(error) from error

    # --- Garde (côté détenteur) ---------------------------------------------------------------

    @app.get("/holders", response_model=list[HolderView], tags=["garde"],
             summary="Détenteurs servis et ce que chaque service laisse sortir")
    def list_holders() -> list[HolderView]:
        return [_holder_view(holder) for holder in guard.holders.values()]

    @app.post("/holders/{holder}/services/{service}", response_model=Envelope, tags=["garde"],
              summary="Interroger un service d'un détenteur au travers de la garde (contrat des registres)",
              responses={400: {"model": Envelope, "description": "Requête mal formée"},
                         404: {"model": Envelope, "description": "Détenteur ou service inconnu"}})
    def guarded_call(
        holder: str,
        service: str,
        body: Annotated[dict[str, Any], Body(description="registry-request (registres/schemas)")],
        x_road_client: Annotated[str | None, Header(description="Demandeur (identifiant X-Road)")] = None,
        x_consent_id: Annotated[str | None, Header(description="Accord du citoyen sur lequel repose la demande")] = None,
    ) -> JSONResponse:
        http_status, envelope = guard.handle(holder, service, body, x_road_client, x_consent_id)
        return JSONResponse(status_code=http_status, content=envelope)

    return app
