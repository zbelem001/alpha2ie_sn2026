"""Client du registre des accords, pour la couche démarches (contrat : consentement-minimisation/openapi.yaml).

CONSENT_URL        adresse de la couche (ex. http://consentement-minimisation:8000)
CONSENT_TOKEN      jeton de service de la couche démarches
CONSENT_TIMEOUT_S  délai d'attente en secondes (défaut : 3)

- ConsentRefused : la couche refuse la demande (accord introuvable, plus actif, données invalides) ;
- ConsentServiceUnavailable : la couche ne répond pas, ou son journal non plus ; rien n'est enregistré.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

DEFAULT_TIMEOUT_S = 3.0

__all__ = ["ConsentClient", "ConsentRefused", "ConsentServiceUnavailable", "consents_from_env"]


class ConsentServiceUnavailable(RuntimeError):
    """La couche consentement-minimisation n'a pas répondu comme prévu."""


class ConsentRefused(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ConsentClient:
    def __init__(self, base_url: str, token: str, *, timeout: float = DEFAULT_TIMEOUT_S,
                 client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = timeout
        self._client = client or httpx.Client()

    def _request(self, method: str, path: str, *, expected: int = 200, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, f"{self.base_url}{path}", headers=self._headers,
                                            timeout=self._timeout, **kwargs)
        except httpx.HTTPError as error:
            raise ConsentServiceUnavailable(f"Couche consentement injoignable ({error.__class__.__name__})") from error
        if response.status_code == expected:
            return response.json()
        if response.status_code in {404, 409, 422}:
            detail = response.json().get("detail") if "json" in response.headers.get("content-type", "") else None
            raise ConsentRefused(response.status_code, detail if isinstance(detail, str) else "Demande refusée")
        raise ConsentServiceUnavailable(f"Couche consentement : HTTP {response.status_code}")

    def record(self, consent: Mapping[str, Any]) -> dict[str, Any]:
        """Enregistre la décision du citoyen (remplace l'accord en cours du dossier)."""
        return self._request("POST", "/v1/consents", expected=201, json=dict(consent))

    def revoke(self, consent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/consents/{consent_id}/revoke")

    def get(self, consent_id: str) -> dict[str, Any] | None:
        try:
            return self._request("GET", f"/v1/consents/{consent_id}")
        except ConsentRefused as refused:
            if refused.status_code == 404:
                return None
            raise

    def search(self, *, case_id: str | None = None, subject_ref: str | None = None,
               active: bool | None = None) -> list[dict[str, Any]]:
        params = {key: value for key, value in (("case_id", case_id), ("subject_ref", subject_ref)) if value}
        if active is not None:
            params["active"] = "true" if active else "false"
        return self._request("GET", "/v1/consents", params=params)

    def active(self, case_id: str) -> dict[str, Any] | None:
        """L'accord actif du dossier (accordé, ni retiré ni expiré), ou None."""
        found = self.search(case_id=case_id, active=True)
        return found[0] if found else None

    def close(self) -> None:
        self._client.close()


def consents_from_env(env: Mapping[str, str] | None = None) -> ConsentClient:
    env = os.environ if env is None else env
    url, token = env.get("CONSENT_URL"), env.get("CONSENT_TOKEN")
    if not url or not token:
        raise ConsentServiceUnavailable("CONSENT_URL et CONSENT_TOKEN sont requis")
    return ConsentClient(url, token, timeout=float(env.get("CONSENT_TIMEOUT_S") or DEFAULT_TIMEOUT_S))
