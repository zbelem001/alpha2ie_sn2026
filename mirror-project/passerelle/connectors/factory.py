"""Choix du connecteur par variables d'environnement, sans toucher au code de l'orchestrateur.

REGISTRY_CONNECTOR        direct (défaut) | xroad
REGISTRY_ROUTES_FILE      connecteur direct : table organisation -> URL (défaut : routing.yaml)
XROAD_SECURITY_SERVER_URL connecteur xroad : URL du serveur de sécurité du demandeur
XROAD_CLIENT_ID           identifiant X-Road du demandeur (défaut : BF/GOV/ONI/CNIB)
REGISTRY_TIMEOUT_S        délai d'attente en secondes (défaut : 3)

Le connecteur simulé (MockRegistryConnector) reste côté backend (Personne 2).
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from .direct import DEFAULT_ROUTES_FILE, HttpRegistryConnector, load_routes
from .http_base import DEFAULT_TIMEOUT_S, BaseHttpConnector
from .xroad import XRoadConnector

DEFAULT_CLIENT_ID = "BF/GOV/ONI/CNIB"


def build_connector(env: Mapping[str, str] | None = None) -> BaseHttpConnector:
    env = os.environ if env is None else env
    kind = env.get("REGISTRY_CONNECTOR", "direct").strip().lower()
    timeout = float(env.get("REGISTRY_TIMEOUT_S") or DEFAULT_TIMEOUT_S)
    client_id = env.get("XROAD_CLIENT_ID") or DEFAULT_CLIENT_ID

    if kind == "direct":
        routes = load_routes(env.get("REGISTRY_ROUTES_FILE") or DEFAULT_ROUTES_FILE)
        return HttpRegistryConnector(routes, client_id=client_id, timeout=timeout)
    if kind == "xroad":
        url = env.get("XROAD_SECURITY_SERVER_URL")
        if not url:
            raise ValueError("REGISTRY_CONNECTOR=xroad exige XROAD_SECURITY_SERVER_URL")
        return XRoadConnector(url, client_id=client_id, timeout=timeout)
    raise ValueError(f"REGISTRY_CONNECTOR inconnu : {kind!r} (attendu : direct ou xroad)")
