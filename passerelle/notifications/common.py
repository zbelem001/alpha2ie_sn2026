"""Utilitaires des notifications simulées, recopiés de registres/registries/common.

La couche passerelle ne dépend pas de la couche registres : seules ces deux
petites fonctions étaient partagées.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

_FORMAT = "%(levelname)s:     [%(name)s] %(message)s"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def console_logger(name: str) -> logging.Logger:
    """Journaux visibles dans `docker compose logs` (uvicorn ne configure que les siens)."""
    logger = logging.getLogger(name)
    if not any(getattr(handler, "dlnuf_console", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT))
        handler.dlnuf_console = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
