"""Cohérence du banc X-Road avec le reste du projet, sans lancer le banc (5,3 Go de mémoire).

- chaque démarche du catalogue (demarches/scripts/seed_demo.py) a, sur le banc, un demandeur
  (XROAD_CLIENTS de .env.example) qui a droit à chacun de ses services ;
- chaque service publié passe par la garde de la couche consentement-minimisation et y a une règle.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import yaml

MIRROR = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("setup_bench", MIRROR / "passerelle/xroad/configuration/setup_bench.py")
bench = importlib.util.module_from_spec(spec)
sys.modules["setup_bench"] = bench  # les dataclasses du script en ont besoin
spec.loader.exec_module(bench)


def seed_constants() -> dict:
    tree = ast.parse((MIRROR / "demarches/scripts/seed_demo.py").read_text(encoding="utf-8"))
    return {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"QUESTION_DEFINITIONS", "DEMO_PROCEDURES"}}


def xroad_clients() -> dict[str, str]:
    for line in (MIRROR / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("XROAD_CLIENTS="):
            return dict(item.split("=", 1) for item in line.removeprefix("XROAD_CLIENTS=").split(",") if item)
    return {}


def test_every_procedure_has_a_declared_requester_with_its_rights():
    seed = seed_constants()
    services = {definition[0]: (definition[1], definition[2]) for definition in seed["QUESTION_DEFINITIONS"]}
    rights = {f"BF/GOV/{c.member}/{c.subsystem}": {(f"BF/GOV/{m}/{s}", code) for m, s, code in c.allowed}
              for c in bench.CONSUMERS}
    mapping = xroad_clients()
    for procedure in seed["DEMO_PROCEDURES"]:
        requester = mapping.get(procedure["owner"], procedure["owner"])
        assert requester in rights, f"{procedure['code']} : demandeur {requester} absent du banc"
        for question, *_ in procedure["questions"]:
            assert services[question] in rights[requester], f"{procedure['code']} : pas de droit sur {services[question]}"


def test_consumer_rights_point_to_published_services_on_known_servers():
    published = {(p.member, p.subsystem, code) for p in bench.PROVIDERS for code in p.services}
    for consumer in bench.CONSUMERS:
        assert consumer.member in bench.MEMBERS
        assert set(consumer.allowed) <= published, consumer
    hosts = {server.host: set(server.clients) for server in bench.SECURITY_SERVERS}
    for provider in bench.PROVIDERS:
        assert provider.member in bench.MEMBERS and (provider.member, provider.subsystem) in hosts[provider.host]
    for consumer in bench.CONSUMERS:
        assert (consumer.member, consumer.subsystem) in hosts["ss-demandeurs"]


def test_every_published_service_goes_through_the_guard_and_has_a_rule():
    holders = yaml.safe_load((MIRROR / "consentement-minimisation/consent_service/holders.yaml").read_text(encoding="utf-8"))["holders"]
    for provider in bench.PROVIDERS:
        assert provider.base_url.startswith(bench.GUARD + "/")
        holder = holders[provider.base_url.rsplit("/", 1)[1]]
        assert holder["organization"] == f"BF/GOV/{provider.member}/{provider.subsystem}"
        assert set(provider.services) <= set(holder["services"]), provider
