"""Connecteur direct : appelle les registres en REST, sans X-Road.

Sert au développement et de plan de repli. Les registres reçoivent le même corps
et le même en-tête X-Road-Client que via X-Road : passer au connecteur X-Road ne
change rien côté registre.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import yaml

from .http_base import DEFAULT_TIMEOUT_S, BaseHttpConnector, RoutingError

DEFAULT_ROUTES_FILE = Path(__file__).parent / "routing.yaml"


def load_routes(path: Path | str = DEFAULT_ROUTES_FILE) -> dict[str, str]:
    with Path(path).open(encoding="utf-8") as handle:
        routes: Any = yaml.safe_load(handle) or {}
    if not isinstance(routes, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in routes.items()
    ):
        raise ValueError(f"{path} : table organisation -> URL attendue")
    return routes


class HttpRegistryConnector(BaseHttpConnector):
    def __init__(
        self,
        routes: Mapping[str, str],
        *,
        client_id: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(client_id=client_id, timeout=timeout, client=client)
        self.routes = dict(routes)

    def _url(self, organization: str, service: str) -> str:
        base = self.routes.get(organization)
        if base is None:
            raise RoutingError(f"Organisation inconnue de la table de routage : {organization}")
        return f"{base.rstrip('/')}/services/{service}"
