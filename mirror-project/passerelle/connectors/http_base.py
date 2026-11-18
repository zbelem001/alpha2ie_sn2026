"""Logique commune aux connecteurs HTTP (direct et X-Road).

Règle de base : query() ne lève jamais d'exception pour un problème de registre.
Panne, délai dépassé, réponse illisible ou non conforme : la réponse est
« unavailable », sans données. Le connecteur n'invente jamais de réponse.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import httpx

from .envelope import Status, is_well_formed, make_envelope

SERVICE_CODE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DEFAULT_TIMEOUT_S = 3.0


class RoutingError(ValueError):
    """Organisation ou service impossible à adresser."""


class BaseHttpConnector:
    def __init__(
        self,
        *,
        client_id: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        client: httpx.Client | None = None,
    ) -> None:
        self.client_id = client_id
        self.timeout = timeout
        self._client = client or httpx.Client()

    # À fournir par chaque connecteur -------------------------------------------------

    def _url(self, organization: str, service: str) -> str:
        raise NotImplementedError

    def _check_client(self, client_id: str) -> None:
        """Lève RoutingError si l'identifiant du demandeur ne convient pas au transport."""

    def _transport_failure(
        self, organization: str, service: str, request_id: str, response: httpx.Response
    ) -> dict[str, Any] | None:
        """Erreur signalée par la couche de transport elle-même (ex. X-Road), sinon None."""
        return None

    # Contrat RegistryConnector -------------------------------------------------------

    def query(
        self,
        organization: str,
        service: str,
        payload: dict[str, Any],
        *,
        client_id: str | None = None,
        consent_id: str | None = None,
    ) -> dict[str, Any]:
        """Interroge un service. Le corps reste celui du contrat des registres ; deux en-têtes :

        - X-Road-Client : demandeur de cet appel (client_id), par défaut celui du connecteur ;
        - X-Consent-Id : accord du citoyen sur lequel repose l'appel, vérifié côté détenteur
          par la couche consentement-minimisation (un registre l'ignore).
        """
        body = dict(payload)
        if not isinstance(body.get("request_id"), str) or not body["request_id"]:
            body["request_id"] = str(uuid.uuid4())
        request_id: str = body["request_id"]

        def answer(status: Status, message: str) -> dict[str, Any]:
            return make_envelope(
                organization=organization, service=service, status=status, request_id=request_id, message=message
            )

        if not SERVICE_CODE.match(service):
            return answer(Status.INVALID_REQUEST, f"Code de service invalide : {service!r}")
        requester = client_id or self.client_id
        try:
            self._check_client(requester)
        except RoutingError as exc:
            return answer(Status.INVALID_REQUEST, str(exc))
        headers = {"X-Road-Client": requester}
        if consent_id:
            headers["X-Consent-Id"] = consent_id
        try:
            url = self._url(organization, service)
        except RoutingError as exc:
            return answer(Status.INVALID_REQUEST, str(exc))

        try:
            response = self._client.post(
                url,
                json=body,
                headers=headers,
                timeout=self.timeout,
            )
        except httpx.TimeoutException:
            return answer(Status.UNAVAILABLE, "Délai d'attente dépassé")
        except httpx.HTTPError:
            return answer(Status.UNAVAILABLE, "Registre injoignable")

        failure = self._transport_failure(organization, service, request_id, response)
        if failure is not None:
            return failure

        try:
            received = response.json()
        except ValueError:
            received = None

        if not is_well_formed(received) or (received["status"] == Status.OK and not response.is_success):
            if response.is_client_error:
                return answer(Status.INVALID_REQUEST, f"Requête rejetée (HTTP {response.status_code})")
            return answer(Status.UNAVAILABLE, f"Réponse non conforme au contrat (HTTP {response.status_code})")

        received_id = received.get("request_id")
        return make_envelope(
            organization=organization,
            service=service,
            status=Status(received["status"]),
            request_id=received_id if isinstance(received_id, str) else request_id,
            data=received.get("data"),
            message=received.get("message") if isinstance(received.get("message"), str) else None,
            responded_at=received.get("responded_at") if isinstance(received.get("responded_at"), str) else None,
            transport_id=response.headers.get("X-Road-Id"),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BaseHttpConnector:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
