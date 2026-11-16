"""Recherche de fiches : par identifiant pivot, ou par nom, prénoms et date de naissance."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from .envelope import ServiceResult
from .models import Subject

Record = dict[str, Any]


def load_records(path: Path) -> list[Record]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: str) -> str:
    """« Ouédraogo », « OUEDRAOGO » et « ouedraogo » deviennent « OUEDRAOGO » ; « Jean-Marc » devient « JEAN MARC »."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.upper().replace("-", " ").split())


def matches_criteria(record: Record, subject: Subject) -> bool:
    if not subject.has_criteria:
        return False
    if normalize(record["last_name"]) != normalize(subject.last_name or ""):
        return False
    if normalize(record["first_names"]) != normalize(subject.first_names or ""):
        return False
    if record["birth_date"] != subject.birth_date.isoformat():  # type: ignore[union-attr]
        return False
    if subject.birth_place and normalize(record.get("birth_place", "")) != normalize(subject.birth_place):
        return False
    return True


def find_records(records: list[Record], subject: Subject) -> list[Record]:
    if subject.pivot_id:
        return [record for record in records if record["pivot_id"] == subject.pivot_id]
    return [record for record in records if matches_criteria(record, subject)]


def resolve_single(records: list[Record], subject: Subject) -> Record | ServiceResult:
    """Renvoie la fiche unique, ou le résultat à transmettre tel quel (aucune fiche, ou plusieurs)."""
    found = find_records(records, subject)
    if not found:
        return ServiceResult.not_found()
    if len(found) > 1:
        return ServiceResult.ambiguous()
    return found[0]
