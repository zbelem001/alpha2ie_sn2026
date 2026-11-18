"""Spécification OpenAPI de la couche et schéma d'un accord, générés depuis l'application.

Après un changement d'API (les tests de test_contract le vérifient) :
    python -m consent_service.openapi
réécrit openapi.yaml et schemas/consent.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from journal_client import MemoryJournal
from sqlalchemy import create_engine

from .app import create_app
from .holders import load_holders
from .schemas import Consent

LAYER = Path(__file__).resolve().parents[1]
SPEC_FILE = LAYER / "openapi.yaml"
CONSENT_SCHEMA_FILE = LAYER / "schemas" / "consent.json"


def specification() -> dict[str, Any]:
    app = create_app(engine=create_engine("sqlite://"), journal=MemoryJournal(), tokens={}, holders=load_holders())
    return app.openapi()


def consent_schema() -> dict[str, Any]:
    schema = Consent.model_json_schema()
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "consent.json", **schema}


def render_specification() -> str:
    return yaml.safe_dump(specification(), sort_keys=False, allow_unicode=True, width=110)


def render_consent_schema() -> str:
    return json.dumps(consent_schema(), ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    SPEC_FILE.write_text(render_specification(), encoding="utf-8")
    CONSENT_SCHEMA_FILE.write_text(render_consent_schema(), encoding="utf-8")
    print(f"Écrits : {SPEC_FILE.name}, schemas/{CONSENT_SCHEMA_FILE.name}")
