"""Accès au registre des accords de la couche consentement-minimisation (consentement-minimisation/).

La couche démarches recueille la décision du citoyen (espace usager, code au guichet) et la fait
enregistrer là-bas ; le registre des accords l'inscrit au journal. Chaque vérification part
ensuite avec la référence de l'accord (en-tête X-Consent-Id), que la garde du détenteur contrôle.
Configuration : CONSENT_URL, CONSENT_TOKEN ; les tests y branchent le service en mémoire.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Protocol

from consent_client import ConsentRefused, ConsentServiceUnavailable, consents_from_env

__all__ = ["ConsentRefused", "ConsentServiceUnavailable", "Consents", "consents", "requester_client", "use_consents"]


class Consents(Protocol):
    def record(self, consent: dict[str, Any]) -> dict[str, Any]: ...

    def revoke(self, consent_id: str) -> dict[str, Any]: ...

    def get(self, consent_id: str) -> dict[str, Any] | None: ...

    def search(self, *, case_id: str | None = None, subject_ref: str | None = None,
               active: bool | None = None) -> list[dict[str, Any]]: ...

    def active(self, case_id: str) -> dict[str, Any] | None: ...


_consents: Consents | None = None
_lock = threading.Lock()


def consents() -> Consents:
    """Le registre des accords configuré ; lève ConsentServiceUnavailable si CONSENT_URL ou CONSENT_TOKEN manque."""
    global _consents
    with _lock:
        if _consents is None:
            _consents = consents_from_env()
        return _consents


def use_consents(client: Consents | None) -> None:
    """Remplace le registre des accords (tests) ; None : retour à la configuration par l'environnement."""
    global _consents
    with _lock:
        _consents = client


def requester_client(administration_code: str) -> str:
    """Demandeur annoncé au détenteur (en-tête X-Road-Client) pour une administration.

    XROAD_CLIENTS="BF/GOV/FONCTION-PUBLIQUE=BF/GOV/FONCTION-PUBLIQUE/RECRUTEMENT,…" associe une
    administration à son sous-système X-Road (banc X-Road) ; sans entrée, son propre code.
    """
    for item in (os.environ.get("XROAD_CLIENTS") or "").split(","):
        code, separator, client = item.strip().partition("=")
        if separator and code.strip() == administration_code and client.strip():
            return client.strip()
    return administration_code
