"""Connecteurs vers les registres.

Ils respectent structurellement le Protocol RegistryConnector du backend :

    query(organization: str, service: str, payload: dict) -> dict

Le payload suit contracts/schemas/registry-request.json, la réponse
contracts/schemas/registry-response.json.
"""

from .direct import HttpRegistryConnector, load_routes
from .envelope import Status
from .factory import build_connector
from .http_base import BaseHttpConnector, RoutingError
from .xroad import XRoadConnector

__all__ = [
    "BaseHttpConnector",
    "HttpRegistryConnector",
    "RoutingError",
    "Status",
    "XRoadConnector",
    "build_connector",
    "load_routes",
]
