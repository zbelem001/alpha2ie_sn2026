"""Spécification OpenAPI de la couche, générée depuis l'application.

Régénérer journal/openapi.yaml après un changement d'API (le test test_contract le vérifie) :
    python -m journal_service.openapi > openapi.yaml
"""

from __future__ import annotations

import sys
from typing import Any

import yaml
from sqlalchemy import create_engine

from .app import create_app


def specification() -> dict[str, Any]:
    return create_app(engine=create_engine("sqlite://"), write_tokens={}, read_tokens={}).openapi()


def render(spec: dict[str, Any]) -> str:
    return yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=110)


if __name__ == "__main__":
    sys.stdout.write(render(specification()))
