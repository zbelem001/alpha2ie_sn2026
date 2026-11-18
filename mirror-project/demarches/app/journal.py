"""Accès à la couche journal (journal/) : chaque événement d'un dossier y est inscrit.

Fermé par défaut : si le journal n'inscrit pas l'événement, l'opération est annulée (503), pour
qu'aucune action sur un dossier n'existe sans sa trace. Configuration : JOURNAL_URL, JOURNAL_TOKEN
(voir journal/README.md). Les tests remplacent le journal par journal_client.MemoryJournal.
"""

from __future__ import annotations

import threading
from typing import Any, Protocol

from journal_client import JournalUnavailable, journal_from_env

__all__ = ["Journal", "JournalUnavailable", "journal", "use_journal"]


class Journal(Protocol):
    def append(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, event_id: str) -> dict[str, Any] | None: ...

    def search(self, *, limit: int | None = None, **filters: Any) -> list[dict[str, Any]]: ...


_journal: Journal | None = None
_lock = threading.Lock()


def journal() -> Journal:
    """Le journal configuré ; lève JournalUnavailable si JOURNAL_URL ou JOURNAL_TOKEN manque."""
    global _journal
    with _lock:
        if _journal is None:
            _journal = journal_from_env()
        return _journal


def use_journal(client: Journal | None) -> None:
    """Remplace le journal (tests) ; None : retour à la configuration par l'environnement."""
    global _journal
    with _lock:
        _journal = client
