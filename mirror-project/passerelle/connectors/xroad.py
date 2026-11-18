"""Connecteur X-Road : passe par le serveur de sécurité du demandeur (protocole REST X-Road).

    POST {serveur de sécurité}/r1/{INSTANCE}/{CLASSE}/{MEMBRE}/{SOUS-SYSTÈME}/{service}
    X-Road-Client: {INSTANCE}/{CLASSE}/{MEMBRE}/{SOUS-SYSTÈME du demandeur}

Les erreurs propres à X-Road arrivent avec l'en-tête X-Road-Error ; elles sont
traduites en statuts du contrat. L'identifiant du message (X-Road-Id) est conservé
dans transport_id.

Validé sur le banc X-Road 7.8.3 (interoperability/xroad) : réponses ok,
not_found, ambiguous, invalid_request, refus hors droits d'accès, service inconnu.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from .envelope import Status, make_envelope
from .http_base import DEFAULT_TIMEOUT_S, BaseHttpConnector, RoutingError

IDENTIFIER_PART = re.compile(r"^[A-Za-z0-9._-]+$")

# Fragments du type d'erreur X-Road -> statut du contrat. Tout le reste => unavailable.
# X-Road 7 écrit « server.serverproxy.access_denied », X-Road 6 « Server.ServerProxy.AccessDenied » :
# la comparaison se fait sans casse ni tirets bas.
_REFUSED_MARKERS = ("accessdenied",)
_INVALID_MARKERS = ("unknownservice", "invalidrequest", "invalidclientidentifier", "unknownmember", "unknownsubsystem")


def _normalize(error_type: str) -> str:
    return error_type.lower().replace("_", "")


def _check_identifier(value: str, parts: int, label: str) -> None:
    segments = value.split("/")
    if len(segments) != parts or not all(IDENTIFIER_PART.match(segment) for segment in segments):
        raise RoutingError(f"{label} X-Road invalide (INSTANCE/CLASSE/MEMBRE/SOUS-SYSTÈME attendu) : {value}")


class XRoadConnector(BaseHttpConnector):
    def __init__(
        self,
        security_server_url: str,
        *,
        client_id: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        client: httpx.Client | None = None,
    ) -> None:
        _check_identifier(client_id, 4, "Identifiant client")
        super().__init__(client_id=client_id, timeout=timeout, client=client)
        self.security_server_url = security_server_url.rstrip("/")

    def _check_client(self, client_id: str) -> None:
        # Demandeur propre à l'appel : un sous-système X-Road déclaré, comme celui du connecteur.
        _check_identifier(client_id, 4, "Identifiant client")

    def _url(self, organization: str, service: str) -> str:
        _check_identifier(organization, 4, "Organisation")
        return f"{self.security_server_url}/r1/{organization}/{service}"

    def _transport_failure(
        self, organization: str, service: str, request_id: str, response: httpx.Response
    ) -> dict[str, Any] | None:
        error_type = response.headers.get("X-Road-Error")
        if not error_type:
            return None
        normalized = _normalize(error_type)
        if any(marker in normalized for marker in _REFUSED_MARKERS):
            status, message = Status.REFUSED, f"Accès refusé par le serveur de sécurité ({error_type})"
        elif any(marker in normalized for marker in _INVALID_MARKERS):
            status, message = Status.INVALID_REQUEST, f"Requête refusée par X-Road ({error_type})"
        else:
            status, message = Status.UNAVAILABLE, f"Échange X-Road impossible ({error_type})"
        return make_envelope(
            organization=organization,
            service=service,
            status=status,
            request_id=request_id,
            message=message,
            transport_id=response.headers.get("X-Road-Id"),
        )
