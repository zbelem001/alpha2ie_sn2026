"""Brancher le registre d'une autre équipe sur notre passerelle, pile démarrée, sans rien reconstruire.

Depuis  (bibliothèque standard seulement) :

    python3 passerelle/brancher.py liste
    python3 passerelle/brancher.py sonder http://192.168.1.42:8000 --essai ACTE:OUAGA:2004:01234
    python3 passerelle/brancher.py remplacer etat-civil http://192.168.1.42:8000 --essai ACTE:OUAGA:2004:01234
    python3 passerelle/brancher.py ajouter equipe-b http://192.168.1.42:8000 \\
        --organisation BF/GOV/EQUIPE-B/ETAT-CIVIL --nom "État civil, équipe B" \\
        --regle is-adult=keep:adult --regle identity=found
    python3 passerelle/brancher.py retirer etat-civil

« remplacer » fait interroger par la garde le registre de l'autre équipe à la place du nôtre,
avec les mêmes règles : nos démarches l'utilisent aussitôt. « ajouter » déclare un nouveau
détenteur (règles et route) ; il reste à créer ses questions dans la couche démarches.

Avant d'écrire quoi que ce soit, l'outil sonde le registre : santé, services proposés (GET
/services ou fichier OpenAPI), et avec --essai, un appel par service pour vérifier que la règle de
minimisation s'applique à ses réponses (champs présents et de bon type ; seuls les noms des
champs sont affichés, jamais les valeurs). Il écrit ensuite un fichier dans
infrastructure/branchements/, que la garde (consentement-minimisation) et la passerelle relisent à
chaque appel, puis attend que la garde l'ait pris en compte.

--sonde URL : adresse à sonder depuis cette machine, si elle diffère de celle que joint la garde
(ex. registre d'essai publié sur un port de la machine).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

MIRROR = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = MIRROR / "infrastructure" / "branchements"
DEFAULT_GUARD = "http://localhost:8109"
GUARD_IN_STACK = "http://consentement-minimisation:8000"

Http = Callable[[str, str, dict | None], tuple[int, Any]]


def http(method: str, url: str, body: dict | None = None) -> tuple[int, Any]:
    """Appel HTTP JSON ; (0, message) si l'adresse ne répond pas."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            content = reply.read()
            return reply.status, json.loads(content) if content else None
    except urllib.error.HTTPError as error:
        content = error.read()
        try:
            return error.code, json.loads(content) if content else None
        except ValueError:
            return error.code, None
    except (urllib.error.URLError, OSError, ValueError) as error:
        return 0, str(error)


# --- Règles -------------------------------------------------------------------------------------


def parse_rule(text: str) -> tuple[str, dict[str, Any]]:
    """« is-adult=keep:adult », « identity=found », « is-adult=adult_from:birth_date@identity »."""
    service, separator, rule = text.partition("=")
    if not separator or not service:
        raise ValueError(f"Règle illisible : {text!r} (service=keep:champ, service=found ou service=adult_from:champ)")
    rule, _, registry_service = rule.partition("@")
    kind, _, argument = rule.partition(":")
    if kind == "keep" and argument:
        parsed: dict[str, Any] = {"keep": {name: "boolean" for name in argument.split(",") if name}}
    elif kind == "found" and not argument:
        parsed = {"found": True}
    elif kind == "adult_from" and argument:
        parsed = {"adult_from": argument}
    else:
        raise ValueError(f"Règle illisible : {text!r}")
    if registry_service:
        parsed["registry_service"] = registry_service
    return service, parsed


def rule_fits(reduction: dict[str, Any], data: Any) -> tuple[bool, str]:
    """La règle s'applique-t-elle à cette réponse « ok » ? Message sans aucune valeur."""
    if not isinstance(data, dict):
        return False, "réponse sans données"
    if reduction.get("found"):
        return True, "fiche retrouvée"
    if "adult_from" in reduction:
        try:
            date.fromisoformat(data.get(reduction["adult_from"]))
            return True, f"date lisible dans « {reduction['adult_from']} »"
        except (TypeError, ValueError):
            return False, f"pas de date lisible dans « {reduction['adult_from']} »"
    missing = [name for name in reduction.get("keep", {}) if type(data.get(name)) is not bool]
    if missing:
        return False, f"champs absents ou non booléens : {', '.join(missing)}"
    return True, "champs " + ", ".join(reduction.get("keep", {}))


# --- Sonde --------------------------------------------------------------------------------------


def openapi_services(path: str) -> set[str]:
    """Services décrits par un fichier OpenAPI (JSON, ou YAML si PyYAML est installé)."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        spec = json.loads(text)
    except ValueError:
        import yaml  # noqa: PLC0415 - seulement pour un fichier YAML

        spec = yaml.safe_load(text)
    services = set()
    for route, operations in (spec.get("paths") or {}).items():
        if route.startswith("/services/") and "{" not in route:
            services.add(route.removeprefix("/services/"))
        elif route == "/services/{service}":
            for operation in operations.values() if isinstance(operations, dict) else []:
                for parameter in operation.get("parameters", []) if isinstance(operation, dict) else []:
                    services.update(parameter.get("schema", {}).get("enum", []))
    return services


def probe(url: str, wanted: dict[str, dict[str, Any]], *, trial: str | None, openapi: str | None,
          call: Http = http, out: Callable[[str], None] = print) -> bool:
    """Sonde le registre ; vrai si chaque service voulu existe et, avec --essai, si sa règle s'applique."""
    base = url.rstrip("/")
    status, health = call("GET", f"{base}/health", None)
    out(f"  santé : {'joignable' if status == 200 else f'injoignable ({health})' if status == 0 else f'HTTP {status}'}")
    if status == 0:
        return False
    offered: set[str] | None = None
    status, listing = call("GET", f"{base}/services", None)
    if status == 200 and isinstance(listing, dict) and isinstance(listing.get("services"), list):
        offered = set(listing["services"])
        out(f"  services annoncés : {', '.join(sorted(offered)) or 'aucun'}")
    if openapi:
        described = openapi_services(openapi)
        out(f"  services décrits par {Path(openapi).name} : {', '.join(sorted(described)) or 'aucun'}")
        offered = described if offered is None else offered | described
    good = True
    for service, rule in wanted.items():
        called = rule.get("registry_service") or service
        line = f"  {service}" + (f" (appelle {called})" if called != service else "")
        if offered is not None and called not in offered:
            out(f"{line} : absent du registre")
            good = False
            continue
        if not trial:
            out(f"{line} : présent" if offered is not None else f"{line} : non vérifié (ni /services ni OpenAPI)")
            continue
        status, answer = call("POST", f"{base}/services/{called}", {
            "request_id": "essai-branchement", "procedure": "essai-branchement",
            "subject": {"pivot_id": trial}, "parameters": {},
        })
        if status not in (200, 400, 404) or not isinstance(answer, dict) or "status" not in answer:
            out(f"{line} : réponse hors contrat (HTTP {status})")
            good = False
        elif answer["status"] != "ok":
            out(f"{line} : {answer['status']} pour la personne d'essai (règle non vérifiée)")
        else:
            fits, why = rule_fits(rule, answer.get("data"))
            fields = ", ".join(sorted(answer["data"])) if isinstance(answer.get("data"), dict) else "—"
            out(f"{line} : champs reçus [{fields}] ; règle {'applicable' if fits else 'NON applicable'} ({why})")
            good = good and fits
    return good


# --- Fichiers de branchement ---------------------------------------------------------------------


def write_plug(directory: Path, name: str, content: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    temporary = directory / f".{name}.json.tmp"
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def guard_holders(guard: str, call: Http = http) -> list[dict[str, Any]] | None:
    status, holders = call("GET", f"{guard.rstrip('/')}/holders", None)
    return holders if status == 200 and isinstance(holders, list) else None


def wait_for_guard(guard: str, check: Callable[[list[dict[str, Any]]], bool], *, call: Http = http,
                   attempts: int = 10, pause: float = 1.0) -> bool:
    for _ in range(attempts):
        holders = guard_holders(guard, call)
        if holders is not None and check(holders):
            return True
        time.sleep(pause)
    return False


def stamp(url: str) -> dict[str, str]:
    return {"registre": url, "le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outil": "passerelle/brancher.py"}


# --- Commandes -----------------------------------------------------------------------------------


def run(argv: list[str], *, call: Http = http, out: Callable[[str], None] = print, pause: float = 1.0) -> int:
    parser = argparse.ArgumentParser(prog="brancher.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--garde", default=DEFAULT_GUARD, help=f"garde depuis cette machine (défaut {DEFAULT_GUARD})")
    parser.add_argument("--dossier", type=Path, default=DEFAULT_DIRECTORY, help="dossier des fichiers de branchement")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("liste", help="détenteurs servis par la garde, et leur origine")
    for name in ("sonder", "remplacer", "ajouter"):
        command = commands.add_parser(name)
        if name != "sonder":
            command.add_argument("detenteur")
        command.add_argument("url", help="adresse du registre, telle que la garde la joint")
        command.add_argument("--sonde", help="adresse à sonder depuis cette machine, si elle diffère")
        command.add_argument("--essai", metavar="PIVOT", help="identifiant d'une personne d'essai (citoyens fictifs du jury)")
        command.add_argument("--openapi", help="fichier OpenAPI du registre")
        command.add_argument("--force", action="store_true", help="écrire même si la sonde échoue")
        if name in ("sonder", "ajouter"):
            command.add_argument("--regle", action="append", default=[], help="service=keep:champ | found | adult_from:champ[@service]")
        if name == "ajouter":
            command.add_argument("--organisation", required=True, help="identifiant X-Road du détenteur")
            command.add_argument("--nom", required=True)
    commands.add_parser("retirer").add_argument("nom", help="nom du branchement (détenteur)")
    args = parser.parse_args(argv)

    if args.command == "liste":
        holders = guard_holders(args.garde, call)
        if holders is None:
            out(f"Garde injoignable ({args.garde})")
            return 1
        for holder in holders:
            out(f"{holder['slug']:<12} {holder['organization']:<34} {holder['registry_url']:<36} {holder['origin']}")
        return 0

    if args.command == "retirer":
        path = args.dossier / f"{args.nom}.json"
        if not path.exists():
            out(f"Aucun branchement « {args.nom} » dans {args.dossier}")
            return 1
        path.unlink()
        out(f"Branchement retiré : {path.name}")
        if wait_for_guard(args.garde, lambda hs: all(h["origin"] != path.name for h in hs), call=call, pause=pause):
            out("La garde est revenue à sa configuration sans ce branchement.")
        return 0

    rules = dict(parse_rule(text) for text in getattr(args, "regle", []))
    holders = guard_holders(args.garde, call)
    if args.command == "remplacer":
        if holders is None:
            out(f"Garde injoignable ({args.garde}) : impossible de connaître les règles de « {args.detenteur} »")
            return 1
        current = next((h for h in holders if h["slug"] == args.detenteur), None)
        if current is None:
            out(f"Détenteur inconnu : {args.detenteur} (connus : {', '.join(h['slug'] for h in holders)})")
            return 1
        rules = {rule["service"]: {**rule["reduction"], "registry_service": rule["registry_service"]}
                 for rule in current["services"]}
        out(f"Remplacer le registre de « {current['name']} » ({current['registry_url']}) par {args.url}")
    elif args.command == "ajouter":
        if not rules:
            out("Au moins une --regle est nécessaire pour un nouveau détenteur")
            return 1
        out(f"Ajouter le détenteur « {args.nom} » ({args.organisation}) : {args.url}")
    else:
        out(f"Sonder {args.url}")

    good = probe(args.sonde or args.url, rules, trial=args.essai, openapi=args.openapi, call=call, out=out)
    if args.command == "sonder":
        return 0 if good else 1
    if not good and not args.force:
        out("Rien n'est écrit : corriger, ou relancer avec --force.")
        return 1

    if args.command == "remplacer":
        content = {"_branchement": stamp(args.url), "holders": {args.detenteur: {"registry_url": args.url}}}
    else:
        services = {}
        for service, rule in rules.items():
            entry = {key: value for key, value in rule.items() if key != "registry_service" or value != service}
            services[service] = entry
        content = {
            "_branchement": stamp(args.url),
            "holders": {args.detenteur: {"organization": args.organisation, "name": args.nom,
                                         "registry_url": args.url, "services": services}},
            "routes": {args.organisation: f"{GUARD_IN_STACK}/holders/{args.detenteur}"},
        }
    path = write_plug(args.dossier, args.detenteur, content)
    out(f"Écrit : {path}")
    if wait_for_guard(args.garde, lambda hs: any(h["slug"] == args.detenteur and h["origin"] == path.name
                                                   and h["registry_url"] == args.url for h in hs), call=call, pause=pause):
        out(f"Branché : la garde interroge {args.url} pour « {args.detenteur} », dès la prochaine demande.")
    else:
        out("La garde n'a pas encore pris le fichier en compte : voir GET /health de la garde "
            "(branchement_error) et `docker compose logs consentement-minimisation`.")
        return 1
    if args.command == "ajouter":
        out("Reste, dans la couche démarches (console d'administration locale) : les questions de ce détenteur, "
            "leur droit d'échange et la démarche qui les pose.")
    out(f"Débrancher : python3 passerelle/brancher.py retirer {args.detenteur}")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
