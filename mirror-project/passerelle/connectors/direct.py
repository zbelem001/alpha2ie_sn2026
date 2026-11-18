"""Connecteur direct : appelle les registres en REST, sans X-Road.

Sert au développement et de plan de repli. Les registres reçoivent le même corps
et le même en-tête X-Road-Client que via X-Road : passer au connecteur X-Road ne
change rien côté registre.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import yaml

from .http_base import DEFAULT_TIMEOUT_S, BaseHttpConnector, RoutingError

DEFAULT_ROUTES_FILE = Path(__file__).parent / "routing.yaml"
OVERLAY_SUFFIXES = {".yaml", ".yml", ".json"}
logger = logging.getLogger(__name__)


def load_routes(path: Path | str = DEFAULT_ROUTES_FILE) -> dict[str, str]:
    with Path(path).open(encoding="utf-8") as handle:
        routes: Any = yaml.safe_load(handle) or {}
    if not isinstance(routes, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in routes.items()
    ):
        raise ValueError(f"{path} : table organisation -> URL attendue")
    return routes


def load_route_overrides(directory: Path | str | None) -> dict[str, str]:
    """Routes ajoutées par les fichiers de branchement (clé « routes »), dans l'ordre de leurs noms.

    Lues à chaque construction du connecteur : un détenteur branché est joignable dès l'appel
    suivant. Un fichier illisible est signalé et ignoré.
    """
    routes: dict[str, str] = {}
    if not directory or not Path(directory).is_dir():
        return routes
    for path in sorted(Path(directory).iterdir()):
        if path.suffix not in OVERLAY_SUFFIXES or path.name.startswith(".") or not path.is_file():
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            added = raw.get("routes") if isinstance(raw, dict) else None
            if added is None:
                continue
            if not isinstance(added, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in added.items()):
                raise ValueError("« routes » : table identifiant X-Road -> URL attendue")
        except (OSError, ValueError, yaml.YAMLError) as error:
            logger.error("Branchement %s ignoré : %s", path.name, error)
            continue
        routes.update(added)
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
