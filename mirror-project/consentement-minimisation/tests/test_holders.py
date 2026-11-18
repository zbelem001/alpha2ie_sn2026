"""Fichier des détenteurs : chargement, contrôles, réductions."""

from __future__ import annotations

from datetime import date

import pytest

from consent_service.holders import NonConforming, ServiceRule, load_holders, parse_holders


def holder(services: dict, **overrides) -> dict:
    entry = {"organization": "BF/GOV/X/Y", "name": "X", "registry_url": "http://x:8000", "services": services}
    entry.update(overrides)
    return {"holders": {"x": entry}}


def test_the_shipped_holders_file_covers_every_simulated_registry():
    holders = load_holders()
    assert {holder.organization for holder in holders.values()} == {
        "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL", "BF/GOV/JUSTICE/REGISTRES", "BF/GOV/ONI/CNIB",
        "BF/GOV/TRESOR/PAIEMENTS", "BF/GOV/TRANSPORT/PERMIS", "BF/GOV/POLICE/PERTES",
    }
    assert holders["etat-civil"].services["identity"].found is True


@pytest.mark.parametrize("services", [
    {"is-adult": {"keep": {"adult": "boolean"}, "found": True}},
    {"is-adult": {}},
    {"is-adult": {"keep": {"adult": "texte"}}},
    {"is-adult": {"keep": {"adult": "boolean"}, "mystere": 1}},
    {"is-adult": {"keep": {"adult": "boolean"}, "basis": "citizen_request"}},
    {"is-adult": {"keep": {"adult": "boolean"}, "basis": "autre"}},
    {"Is Adult": {"keep": {"adult": "boolean"}}},
])
def test_invalid_rules_are_refused_at_load(services):
    with pytest.raises(ValueError):
        parse_holders(holder(services))


def test_a_holder_is_declared_once():
    raw = holder({"a": {"found": True}})
    raw["holders"]["z"] = dict(raw["holders"]["x"])
    with pytest.raises(ValueError):
        parse_holders(raw)


def test_reductions():
    keep = ServiceRule("is-adult", keep={"adult": "boolean"})
    assert keep.reduce({"adult": False, "birth_date": "2010-01-01"}, date(2026, 11, 18)) == {"adult": False}
    with pytest.raises(NonConforming):
        keep.reduce({"adult": 1}, date(2026, 11, 18))
    assert ServiceRule("identity", found=True).reduce({"last_name": "KABORE"}, date(2026, 11, 18)) == {"found": True}

    adult = ServiceRule("is-adult", adult_from="birth_date")
    assert adult.reduce({"birth_date": "2008-11-18"}, date(2026, 11, 18)) == {"adult": True}
    assert adult.reduce({"birth_date": "2008-11-19"}, date(2026, 11, 18)) == {"adult": False}
    for broken in ({}, {"birth_date": "18/11/2008"}, {"birth_date": 2008}):
        with pytest.raises(NonConforming):
            adult.reduce(broken, date(2026, 11, 18))
