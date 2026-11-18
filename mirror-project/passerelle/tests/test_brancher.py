"""Outil « brancher un registre » (passerelle/brancher.py) et routes des fichiers de branchement."""

from __future__ import annotations

import json

import pytest

import brancher
from connectors import build_connector
from connectors.direct import load_route_overrides

GUARD = "http://garde"
THEIRS = "http://equipe-b:8000"
AWA = "ACTE:OUAGA:2004:01234"
BASE = [{
    "slug": "etat-civil", "organization": "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL", "name": "État civil",
    "registry_url": "http://civil-registry:8000", "origin": "base",
    "services": [
        {"service": "is-adult", "registry_service": "is-adult", "reduction": {"keep": {"adult": "boolean"}}},
        {"service": "identity", "registry_service": "identity", "reduction": {"found": True}},
    ],
}]


class World:
    """Garde (qui lit le dossier des branchements, comme la vraie) et registre de l'autre équipe."""

    def __init__(self, directory, answers=None, services=("is-adult", "identity")) -> None:
        self.directory = directory
        self.answers = answers or {"is-adult": {"adult": True}, "identity": {"last_name": "KABORE", "birth_date": "2004-03-12"}}
        self.services = list(services)
        self.calls = []

    def holders(self):
        holders = json.loads(json.dumps(BASE))
        for path in sorted(self.directory.glob("*.json")):
            content = json.loads(path.read_text(encoding="utf-8"))
            for slug, entry in content["holders"].items():
                current = next((h for h in holders if h["slug"] == slug), None)
                if current is None:
                    current = {"slug": slug, "services": [], **{k: entry[k] for k in ("organization", "name")}}
                    holders.append(current)
                current.update(registry_url=entry["registry_url"], origin=path.name)
        return holders

    def __call__(self, method, url, body=None):
        self.calls.append((method, url, body))
        if url == f"{GUARD}/holders":
            return 200, self.holders()
        if url == f"{THEIRS}/health":
            return 200, {"status": "up"}
        if url == f"{THEIRS}/services":
            return 200, {"services": self.services}
        if method == "POST" and url.startswith(f"{THEIRS}/services/"):
            service = url.rsplit("/", 1)[1]
            return 200, {"request_id": body["request_id"], "organization": "X", "service": service, "status": "ok",
                         "data": self.answers[service], "message": None, "responded_at": "2026-11-18T10:00:00Z"}
        return 0, "injoignable"


def run(world, *args):
    lines = []
    code = brancher.run(["--garde", GUARD, "--dossier", str(world.directory), *args], call=world, out=lines.append, pause=0)
    return code, "\n".join(lines)


def test_rules_are_read_from_the_command_line():
    assert brancher.parse_rule("is-adult=keep:adult") == ("is-adult", {"keep": {"adult": "boolean"}})
    assert brancher.parse_rule("identity=found") == ("identity", {"found": True})
    assert brancher.parse_rule("is-adult=adult_from:birth_date@identity") == (
        "is-adult", {"adult_from": "birth_date", "registry_service": "identity"})
    for broken in ("is-adult", "is-adult=keep:", "is-adult=autre:x", "=found"):
        with pytest.raises(ValueError):
            brancher.parse_rule(broken)


def test_a_rule_fits_an_answer_without_showing_its_values():
    assert brancher.rule_fits({"keep": {"adult": "boolean"}}, {"adult": True})[0]
    fits, why = brancher.rule_fits({"keep": {"adult": "boolean"}}, {"adult": "oui"})
    assert not fits and "oui" not in why
    assert brancher.rule_fits({"adult_from": "birth_date"}, {"birth_date": "2004-03-12"})[0]
    assert not brancher.rule_fits({"adult_from": "birth_date"}, {"birth_date": "12/03/2004"})[0]


def test_replacing_a_registry_after_a_successful_trial(tmp_path):
    world = World(tmp_path)
    code, output = run(world, "remplacer", "etat-civil", THEIRS, "--essai", AWA)
    assert code == 0, output
    content = json.loads((tmp_path / "etat-civil.json").read_text(encoding="utf-8"))
    assert content["holders"] == {"etat-civil": {"registry_url": THEIRS}} and "routes" not in content
    assert "règle applicable" in output and "Branché" in output
    assert "KABORE" not in output and "2004-03-12" not in output  # noms des champs, jamais les valeurs


def test_nothing_is_written_when_a_rule_does_not_fit(tmp_path):
    world = World(tmp_path, answers={"is-adult": {"adult": "oui"}, "identity": {"x": 1}})
    code, output = run(world, "remplacer", "etat-civil", THEIRS, "--essai", AWA)
    assert code == 1 and "NON applicable" in output and not list(tmp_path.glob("*.json"))


def test_a_missing_service_blocks_unless_forced(tmp_path):
    world = World(tmp_path, services=("is-adult",))
    code, output = run(world, "remplacer", "etat-civil", THEIRS)
    assert code == 1 and "identity : absent du registre" in output and not list(tmp_path.glob("*.json"))
    assert run(world, "remplacer", "etat-civil", THEIRS, "--force")[0] == 0
    assert (tmp_path / "etat-civil.json").exists()


def test_adding_a_new_holder_writes_its_rules_and_route(tmp_path):
    world = World(tmp_path)
    code, output = run(world, "ajouter", "equipe-b", THEIRS, "--organisation", "BF/GOV/EQUIPE-B/ETAT-CIVIL",
                       "--nom", "État civil, équipe B", "--regle", "is-adult=adult_from:birth_date@identity",
                       "--essai", AWA)
    assert code == 0, output
    content = json.loads((tmp_path / "equipe-b.json").read_text(encoding="utf-8"))
    assert content["holders"]["equipe-b"]["services"] == {
        "is-adult": {"adult_from": "birth_date", "registry_service": "identity"}}
    assert content["routes"] == {"BF/GOV/EQUIPE-B/ETAT-CIVIL": "http://consentement-minimisation:8000/holders/equipe-b"}
    assert "console d'administration" in output


def test_unplugging(tmp_path):
    world = World(tmp_path)
    run(world, "remplacer", "etat-civil", THEIRS, "--essai", AWA)
    code, output = run(world, "retirer", "etat-civil")
    assert code == 0 and not (tmp_path / "etat-civil.json").exists()
    assert world.holders()[0]["registry_url"] == "http://civil-registry:8000"
    assert run(world, "retirer", "etat-civil")[0] == 1


def test_unknown_holder_or_unreachable_registry(tmp_path):
    world = World(tmp_path)
    assert "Détenteur inconnu" in run(world, "remplacer", "police", THEIRS)[1]
    code, output = run(world, "remplacer", "etat-civil", "http://ailleurs:8000")
    assert code == 1 and "injoignable" in output


def test_services_described_by_an_openapi_file(tmp_path):
    spec = {"paths": {"/services/is-adult": {"post": {}}, "/health": {"get": {}},
                      "/services/{service}": {"post": {"parameters": [{"name": "service", "schema": {"enum": ["identity"]}}]}}}}
    (tmp_path / "contrat.json").write_text(json.dumps(spec), encoding="utf-8")
    assert brancher.openapi_services(str(tmp_path / "contrat.json")) == {"is-adult", "identity"}


def test_plug_files_add_routes_to_the_direct_connector(tmp_path):
    (tmp_path / "equipe-b.json").write_text(json.dumps({"routes": {"BF/GOV/EQUIPE-B/ETAT-CIVIL": "http://garde/holders/equipe-b"}}))
    (tmp_path / "casse.json").write_text("{pas du json")
    (tmp_path / "remplacement.json").write_text(json.dumps({"holders": {"etat-civil": {"registry_url": THEIRS}}}))
    assert load_route_overrides(tmp_path) == {"BF/GOV/EQUIPE-B/ETAT-CIVIL": "http://garde/holders/equipe-b"}
    connector = build_connector({"REGISTRY_ROUTES_OVERRIDES": str(tmp_path)})
    assert connector.routes["BF/GOV/EQUIPE-B/ETAT-CIVIL"] == "http://garde/holders/equipe-b"
    assert "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL" in connector.routes
