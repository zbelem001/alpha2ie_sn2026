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


def holder_matches(record: Record, subject: Subject) -> bool:
    """La fiche appartient-elle au titulaire attendu ? Identifiant pivot, à défaut critères d'identité."""
    if subject.pivot_id:
        return str(record.get("pivot_id", "")) == subject.pivot_id
    if subject.has_criteria and all(key in record for key in ("last_name", "first_names", "birth_date")):
        return matches_criteria(record, subject)
    return False


def resolve_by_identifier(
    records: list[Record], parameters: dict[str, Any], expected_type: str, field: str, subject: Subject
) -> Record | ServiceResult:
    """Retrouve une fiche par la référence propre au registre, puis vérifie son titulaire.

    La référence désigne la pièce ; elle ne prouve pas à qui elle appartient (une référence
    saisie par erreur, ou celle d'un tiers). Une fiche qui n'appartient pas au titulaire attendu
    donne not_found, comme une référence inconnue : rien n'est révélé, et un faux lien est
    pire que pas de lien (docs/resolution-des-donnees.md, §8).
    """
    if not (subject.pivot_id or subject.has_criteria):
        return ServiceResult.invalid("La référence d’une pièce doit être accompagnée de l’identité attendue de son titulaire")
    if parameters.get("identifier_type") != expected_type:
        return ServiceResult.invalid("Type d’identifiant incompatible avec ce registre")
    value = parameters.get("document_identifier")
    if not isinstance(value, str) or not value.strip():
        return ServiceResult.invalid("Identifiant de document manquant")
    normalized = value.strip().upper()
    found = [record for record in records if str(record.get(field, "")).strip().upper() == normalized]
    if not found:
        return ServiceResult.not_found()
    if len(found) > 1:
        return ServiceResult.ambiguous()
    if not holder_matches(found[0], subject):
        return ServiceResult.not_found()
    return found[0]
