"""Détenteurs servis par la garde, et règles de minimisation de chacun de leurs services.

Chaque service déclare :
- sa base : « consent » (un accord valide du citoyen est exigé, défaut) ou « citizen_request »
  (vérification demandée par le citoyen lui-même, limitée aux démarches listées) ;
- sa réduction, une seule parmi :
    keep: {champ: boolean}   ne garder que ces champs, de ce type ;
    found: true              seulement « fiche retrouvée : oui » ;
    adult_from: champ        seulement « majeur : oui/non », calculé depuis une date de naissance
                             (adult_age : 18 par défaut), pour un registre qui renvoie la date ;
- au besoin registry_service : le service du registre à appeler, s'il diffère.

Une réponse « ok » qui ne permet pas d'appliquer la règle (champ absent, mauvais type) devient
« unavailable » : la garde n'invente jamais de réponse et ne laisse rien passer d'autre.
"""

from __future__ import annotations

import copy
import logging
import os
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)
OVERLAY_SUFFIXES = {".yaml", ".yml", ".json"}

DEFAULT_HOLDERS_FILE = Path(__file__).with_name("holders.yaml")
SERVICE_CODE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEEP_TYPES = {"boolean": bool}
BASES = ("consent", "citizen_request")


class NonConforming(ValueError):
    """La réponse du registre ne permet pas d'appliquer la règle."""


def age_on(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def reference_date() -> date:
    """« Aujourd'hui », figé par REFERENCE_DATE (AAAA-MM-JJ) pendant une démonstration, comme les registres."""
    value = os.environ.get("REFERENCE_DATE")
    return date.fromisoformat(value) if value else date.today()


@dataclass(frozen=True)
class ServiceRule:
    service: str
    basis: str = "consent"
    procedures: tuple[str, ...] = ()
    registry_service: str | None = None
    keep: Mapping[str, str] = field(default_factory=dict)
    found: bool = False
    adult_from: str | None = None
    adult_age: int = 18

    @property
    def called_service(self) -> str:
        return self.registry_service or self.service

    def reduction(self) -> dict[str, Any]:
        """Règle de réduction, lisible par une machine (outil « brancher un registre »)."""
        if self.found:
            return {"found": True}
        if self.adult_from:
            return {"adult_from": self.adult_from, "adult_age": self.adult_age}
        return {"keep": dict(self.keep)}

    def transmits(self) -> str:
        if self.found:
            return "fiche retrouvée : oui"
        if self.adult_from:
            return f"majeur ({self.adult_age} ans) : oui ou non, calculé depuis « {self.adult_from} », jamais la date"
        return ", ".join(f"{name} ({kind})" for name, kind in self.keep.items())

    def reduce(self, data: Mapping[str, Any], today: date) -> dict[str, Any]:
        if self.found:
            return {"found": True}
        if self.adult_from:
            raw = data.get(self.adult_from)
            try:
                born = date.fromisoformat(raw) if isinstance(raw, str) else None
            except ValueError:
                born = None
            if born is None:
                raise NonConforming(self.adult_from)
            return {"adult": age_on(born, today) >= self.adult_age}
        reduced = {}
        for name, kind in self.keep.items():
            value = data.get(name)
            if type(value) is not KEEP_TYPES[kind]:
                raise NonConforming(name)
            reduced[name] = value
        return reduced


@dataclass(frozen=True)
class Holder:
    slug: str
    organization: str
    name: str
    registry_url: str
    services: Mapping[str, ServiceRule]
    # « base » (holders.yaml) ou fichier de branchement qui a remplacé ou ajouté ce détenteur.
    origin: str = "base"


def _rule(holder: str, service: str, raw: Any) -> ServiceRule:
    where = f"{holder}/{service}"
    if not SERVICE_CODE.match(service) or not isinstance(raw, dict):
        raise ValueError(f"{where} : code de service ou règle invalide")
    unknown = set(raw) - {"basis", "procedures", "registry_service", "keep", "found", "adult_from", "adult_age"}
    if unknown:
        raise ValueError(f"{where} : clés inconnues {sorted(unknown)}")
    reductions = [key for key in ("keep", "found", "adult_from") if raw.get(key)]
    if len(reductions) != 1:
        raise ValueError(f"{where} : une seule réduction attendue parmi keep, found, adult_from")
    keep = raw.get("keep") or {}
    if not isinstance(keep, dict) or any(kind not in KEEP_TYPES for kind in keep.values()):
        raise ValueError(f"{where} : keep attend {{champ: boolean}}")
    basis = raw.get("basis", "consent")
    procedures = tuple(raw.get("procedures") or ())
    if basis not in BASES:
        raise ValueError(f"{where} : base inconnue {basis!r}")
    if basis == "citizen_request" and not procedures:
        raise ValueError(f"{where} : une vérification demandée par le citoyen doit lister ses démarches")
    registry_service = raw.get("registry_service")
    if registry_service is not None and not SERVICE_CODE.match(registry_service):
        raise ValueError(f"{where} : registry_service invalide")
    return ServiceRule(service=service, basis=basis, procedures=procedures, registry_service=registry_service,
                       keep=dict(keep), found=raw.get("found") is True, adult_from=raw.get("adult_from"),
                       adult_age=int(raw.get("adult_age", 18)))


def parse_holders(raw: Any, origins: Mapping[str, str] | None = None) -> dict[str, Holder]:
    entries = raw.get("holders") if isinstance(raw, dict) else None
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Fichier des détenteurs : une table « holders » non vide est attendue")
    holders: dict[str, Holder] = {}
    for slug, entry in entries.items():
        if not SLUG.match(str(slug)) or not isinstance(entry, dict):
            raise ValueError(f"Détenteur invalide : {slug!r}")
        missing = [key for key in ("organization", "name", "registry_url", "services") if not entry.get(key)]
        if missing:
            raise ValueError(f"{slug} : champs manquants {missing}")
        services = {service: _rule(slug, service, rule) for service, rule in entry["services"].items()}
        holders[slug] = Holder(slug=slug, organization=entry["organization"], name=entry["name"],
                               registry_url=entry["registry_url"], services=services,
                               origin=(origins or {}).get(slug, "base"))
    organizations = [holder.organization for holder in holders.values()]
    if len(organizations) != len(set(organizations)):
        raise ValueError("Un détenteur n'est déclaré qu'une fois")
    return holders


def load_holders(path: str | Path | None = None) -> dict[str, Holder]:
    path = Path(path or os.environ.get("HOLDERS_FILE") or DEFAULT_HOLDERS_FILE)
    with path.open(encoding="utf-8") as handle:
        return parse_holders(yaml.safe_load(handle))


def merge_overlays(base: Any, overlays: list[tuple[str, Any]]) -> tuple[dict[str, Any], dict[str, str]]:
    """Applique les fichiers de branchement au fichier de base, dans l'ordre de leurs noms.

    Un détenteur déjà connu est complété ou corrigé (ex. seulement registry_url : ses règles
    restent celles de la base) ; un détenteur inconnu est ajouté entier.
    """
    if not isinstance(base, dict) or not isinstance(base.get("holders"), dict):
        raise ValueError("Fichier des détenteurs : une table « holders » est attendue")
    entries = copy.deepcopy(base["holders"])
    origins = {slug: "base" for slug in entries}
    for name, raw in overlays:
        added = raw.get("holders") if isinstance(raw, dict) else None
        if added is None:
            continue
        if not isinstance(added, dict):
            raise ValueError(f"{name} : « holders » doit être une table")
        for slug, entry in added.items():
            if not isinstance(entry, dict):
                raise ValueError(f"{name} : détenteur {slug!r} invalide")
            entries[slug] = {**entries.get(slug, {}), **entry}
            origins[slug] = name
    return {"holders": entries}, origins


def overlay_files(directory: str | Path | None) -> list[Path]:
    if not directory or not Path(directory).is_dir():
        return []
    return sorted(path for path in Path(directory).iterdir()
                  if path.suffix in OVERLAY_SUFFIXES and path.is_file() and not path.name.startswith("."))


class HolderCatalog:
    """Détenteurs du fichier de base et des fichiers de branchement (HOLDERS_OVERRIDES), relus dès
    qu'un fichier change : brancher ou débrancher un registre ne demande ni reconstruction ni
    redémarrage. Un fichier invalide est signalé et ignoré : la configuration précédente reste."""

    def __init__(self, path: str | Path | None = None, overrides: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("HOLDERS_FILE") or DEFAULT_HOLDERS_FILE)
        self.overrides = overrides if overrides is not None else os.environ.get("HOLDERS_OVERRIDES")
        self._lock = threading.Lock()
        self._signature: tuple | None = None
        self._holders: dict[str, Holder] | None = None
        self.error: str | None = None

    def _current_signature(self) -> tuple:
        signature = []
        for path in [self.path, *overlay_files(self.overrides)]:
            try:
                stat = path.stat()
            except OSError:  # fichier retiré pendant la lecture : relu au prochain appel
                continue
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(signature)

    def _load(self) -> dict[str, Holder]:
        with self.path.open(encoding="utf-8") as handle:
            base = yaml.safe_load(handle)
        overlays = []
        for path in overlay_files(self.overrides):
            with path.open(encoding="utf-8") as handle:
                overlays.append((path.name, yaml.safe_load(handle)))
        merged, origins = merge_overlays(base, overlays)
        return parse_holders(merged, origins)

    def current(self) -> dict[str, Holder]:
        with self._lock:
            signature = self._current_signature()
            if signature != self._signature:
                try:
                    self._holders, self.error = self._load(), None
                    logger.info("Détenteurs : %s", ", ".join(
                        f"{slug} ({holder.origin})" for slug, holder in sorted(self._holders.items())))
                except (ValueError, OSError, yaml.YAMLError) as error:
                    if self._holders is None:
                        raise
                    self.error = str(error)
                    logger.error("Branchement ignoré, configuration précédente conservée : %s", error)
                self._signature = signature
            return self._holders
