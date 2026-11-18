"""Client HTTP de la couche journal (contrat : journal/openapi.yaml).

JOURNAL_URL        adresse du journal (ex. http://journal:8000)
JOURNAL_TOKEN      jeton de service de la couche appelante
JOURNAL_TIMEOUT_S  délai d'attente en secondes (défaut : 3)
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import httpx

DEFAULT_TIMEOUT_S = 3.0
PAGE_SIZE = 500
_QUERY_NAMES = {"occurred_from": "from", "occurred_to": "to"}


class JournalUnavailable(RuntimeError):
    """Le journal n'a pas répondu comme prévu : l'événement n'est pas inscrit, ou la lecture a échoué."""


def _params(filters: Mapping[str, Any]) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    for key, value in filters.items():
        if value is None:
            continue
        values = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
        for item in values:
            params.append((_QUERY_NAMES.get(key, key), item.isoformat() if isinstance(item, datetime) else str(item)))
    return params


class JournalClient:
    def __init__(self, base_url: str, token: str, *, timeout: float = DEFAULT_TIMEOUT_S,
                 client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = timeout
        self._client = client or httpx.Client()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._client.request(method, f"{self.base_url}{path}", headers=self._headers,
                                        timeout=self._timeout, **kwargs)
        except httpx.HTTPError as error:
            raise JournalUnavailable(f"Journal injoignable ({error.__class__.__name__})") from error

    def append(self, event: Mapping[str, Any]) -> dict[str, Any]:
        """Inscrit l'événement et le renvoie avec son identifiant, sa date et son empreinte."""
        response = self._request("POST", "/v1/events", json=dict(event))
        if response.status_code != 201:
            raise JournalUnavailable(f"Événement non inscrit par le journal (HTTP {response.status_code})")
        return response.json()

    def get(self, event_id: str) -> dict[str, Any] | None:
        response = self._request("GET", f"/v1/events/{event_id}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise JournalUnavailable(f"Lecture du journal impossible (HTTP {response.status_code})")
        return response.json()

    def search(self, *, limit: int | None = None, **filters: Any) -> list[dict[str, Any]]:
        """Tous les événements qui correspondent (pages enchaînées), ou les `limit` premiers.

        Filtres : subject_ref, case_id, correlation_id, event_type (un ou plusieurs), requester_code,
        actor_type, q, occurred_from, occurred_to, order (asc ou desc).
        """
        events: list[dict[str, Any]] = []
        after: int | None = None
        while True:
            size = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(events))
            response = self._request("GET", "/v1/events", params=_params({**filters, "after": after, "limit": size}))
            if response.status_code != 200:
                raise JournalUnavailable(f"Recherche dans le journal impossible (HTTP {response.status_code})")
            page = response.json()
            events.extend(page["events"])
            after = page.get("next_after")
            if after is None or (limit is not None and len(events) >= limit):
                return events

    def close(self) -> None:
        self._client.close()


def journal_from_env(env: Mapping[str, str] | None = None) -> JournalClient:
    env = os.environ if env is None else env
    url, token = env.get("JOURNAL_URL"), env.get("JOURNAL_TOKEN")
    if not url or not token:
        raise JournalUnavailable("JOURNAL_URL et JOURNAL_TOKEN sont requis pour écrire au journal")
    return JournalClient(url, token, timeout=float(env.get("JOURNAL_TIMEOUT_S") or DEFAULT_TIMEOUT_S))
