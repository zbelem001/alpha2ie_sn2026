"""Reprise automatique des vérifications interrompues par un registre indisponible (couche résilience).

Toutes les REGISTRY_RETRY_INTERVAL_S secondes (0 : désactivée), les dossiers qui ont une
vérification « unavailable » et un accord actif sont repris par _run_checks, comme le ferait le
guichet. Le bail sur chaque demande (attempt_lease_expired) empêche tout appel en double, même si
le guichet relance au même moment. Au-delà de REGISTRY_RETRY_MAX_ATTEMPTS tentatives pour une
demande, la reprise automatique s'arrête : l'agent peut toujours relancer depuis le guichet.

Pas de reprise sans accord actif : aucun événement « checks_blocked » répété au journal.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.consents import ConsentServiceUnavailable, consents
from app.database.models import Case, RegistryRequest

logger = logging.getLogger(__name__)
DEFAULT_MAX_ATTEMPTS = 20


def retry_unavailable_checks(sessions: Callable[[], Session], *, max_attempts: int | None = None) -> list[str]:
    """Reprend une fois chaque dossier en attente d'un registre ; renvoie les dossiers repris."""
    from app.api import _run_checks

    from app.api import REQUEST_LEASE_SECONDS

    limit = max_attempts or int(os.environ.get("REGISTRY_RETRY_MAX_ATTEMPTS") or DEFAULT_MAX_ATTEMPTS)
    # Demandes « unavailable », et demandes restées « pending » au-delà du bail (appel interrompu :
    # arrêt du service, journal injoignable au moment d'inscrire la réponse).
    stale = datetime.now(timezone.utc) - timedelta(seconds=REQUEST_LEASE_SECONDS)
    with sessions() as db:
        case_ids = list(db.scalars(select(RegistryRequest.case_id).where(
            RegistryRequest.attempt_count < limit,
            or_(RegistryRequest.status == "unavailable",
                and_(RegistryRequest.status == "pending", RegistryRequest.updated_at < stale)),
        ).distinct()))
    resumed = []
    for case_id in case_ids:
        try:
            if consents().active(str(case_id)) is None:
                continue
        except ConsentServiceUnavailable:
            logger.warning("Reprise suspendue : registre des accords injoignable")
            return resumed
        with sessions() as db:
            case = db.get(Case, case_id)
            if case is None or case.status in {"completed", "rejected", "cancelled"}:
                continue
            try:
                _run_checks(case, db)
                resumed.append(str(case_id))
            except HTTPException as error:
                logger.info("Reprise du dossier %s différée : %s", case_id, error.detail)
            except Exception:  # noqa: BLE001 - une erreur sur un dossier n'arrête pas les autres
                logger.exception("Reprise du dossier %s impossible", case_id)
    return resumed


class RetryWorker:
    """Fil de fond lancé avec l'API (app/main.py)."""

    def __init__(self, sessions: Callable[[], Session], interval: float) -> None:
        self._sessions = sessions
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="reprise-registres", daemon=True)

    def start(self) -> None:
        logger.info("Reprise automatique des registres indisponibles toutes les %ss", self._interval)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                resumed = retry_unavailable_checks(self._sessions)
                if resumed:
                    logger.info("Dossiers repris : %s", ", ".join(resumed))
            except Exception:  # noqa: BLE001 - le fil ne doit jamais s'arrêter
                logger.exception("Tour de reprise interrompu")
