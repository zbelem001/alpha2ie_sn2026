"""Connecteurs vers les registres.

Ils respectent structurellement le Protocol RegistryConnector du backend :

    query(organization: str, service: str, payload: dict) -> dict

Le payload suit contracts/schemas/registry-request.json, la réponse
contracts/schemas/registry-response.json.

NotificationClient envoie les SMS et e-mails (simulés) et lit les réponses du
citoyen : contracts/schemas/notification-*.json et sms-reply.json.
"""

from .direct import HttpRegistryConnector, load_routes
from .envelope import Status
from .factory import build_connector
from .http_base import BaseHttpConnector, RoutingError
from .notifier import NotificationClient, build_notifier
from .xroad import XRoadConnector

__all__ = [
    "BaseHttpConnector",
    "HttpRegistryConnector",
    "NotificationClient",
    "RoutingError",
    "Status",
    "XRoadConnector",
    "build_connector",
    "build_notifier",
    "load_routes",
]
