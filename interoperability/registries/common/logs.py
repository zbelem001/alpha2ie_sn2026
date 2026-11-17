"""Journaux applicatifs visibles dans `docker compose logs`.

uvicorn ne configure que ses propres journaux : sans gestionnaire, les messages
INFO des registres et des notifications seraient perdus.
"""

from __future__ import annotations

import logging

_FORMAT = "%(levelname)s:     [%(name)s] %(message)s"


def console_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(getattr(handler, "dlnuf_console", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT))
        handler.dlnuf_console = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
