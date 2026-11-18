"""Garde côté détenteur, devant les registres simulés : accord exigé, réponse réduite, refus et pannes au journal."""

from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from consent_service.holders import parse_holders

from .conftest import (
    AUTH, AWA, CIVIL, CONCOURS, FONCTION_PUBLIQUE, JUSTICE, PASSEPORT, TRESOR, ask, concours_consent, registry_body,
)


class Untouchable(httpx.Client):
    """Registre qui ne doit pas être appelé (refus avant tout appel)."""

    def request(self, *args, **kwargs):
        raise AssertionError("le registre a été appelé")


def test_only_the_useful_answer_leaves_the_holder(client, journal, granted):
    status, envelope = ask(client, "etat-civil", "is-adult", registry_body(), consent_id=granted["id"])
    assert status == 200 and envelope["status"] == "ok" and envelope["data"] == {"adult": True}
    assert envelope["organization"] == CIVIL and envelope["request_id"] == "requete-1"

    [event] = journal.search(event_type="holder_response")
    assert event["outcome"] == "ok" and event["data_categories"] == ["adult"]
    assert event["consent_id"] == granted["id"] and event["case_id"] == "dossier-awa-1"
    assert event["correlation_id"] == "requete-1" and event["question_code"] == "candidate_minimum_age"
    assert event["requester_code"] == FONCTION_PUBLIQUE and event["holder_code"] == CIVIL
    assert "adult" in event["purpose"] and "2004-03-12" not in json.dumps(event)


def test_a_full_identity_record_becomes_found_only(client, journal):
    consent = client.post("/v1/consents", headers=AUTH, json=concours_consent(
        procedure_code=PASSEPORT, requester_code="BF/GOV/DIPF/PASSEPORTS",
        scope=[{"question_code": "passport_birth_act_found", "holder_code": CIVIL, "service_code": "identity"}],
    )).json()
    status, envelope = ask(client, "etat-civil", "identity", registry_body(PASSEPORT),
                           requester="BF/GOV/DIPF/PASSEPORTS", consent_id=consent["id"])
    assert envelope["data"] == {"found": True}
    # Le registre a renvoyé la fiche complète : rien n'en sort.
    assert not {"KABORE", "2004-03-12", "Ouagadougou", "COMPAORE"} & set(json.dumps(envelope).split('"'))


def test_majority_is_computed_from_a_raw_birth_date_without_sending_it(journal, clock, registries):
    """Registre qui ne sait renvoyer que la fiche (date de naissance) : seule sort « majeur : oui »."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from consent_service.app import create_app
    from .conftest import TODAY, TOKEN

    holders = parse_holders({"holders": {"etat-civil": {
        "organization": CIVIL, "name": "Registre d'une autre équipe", "registry_url": "http://autre-equipe:8000",
        "services": {"is-adult": {"registry_service": "identity", "adult_from": "birth_date"}},
    }}})
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    app = create_app(engine=engine, journal=journal, tokens={TOKEN: "demarches"}, holders=holders,
                     registry_clients=registries, clock=clock, today=lambda: TODAY)
    with TestClient(app) as other:
        consent = other.post("/v1/consents", json=concours_consent(), headers=AUTH).json()
        status, envelope = ask(other, "etat-civil", "is-adult", registry_body(), consent_id=consent["id"])
    assert envelope["data"] == {"adult": True}
    assert "2004" not in json.dumps(envelope)


def test_payment_reference_and_amount_stay_with_the_treasury(client):
    consent = client.post("/v1/consents", headers=AUTH, json=concours_consent(
        procedure_code=PASSEPORT, requester_code="BF/GOV/DIPF/PASSEPORTS",
        scope=[{"question_code": "passport_fiscal_stamp_paid", "holder_code": TRESOR, "service_code": "payment-status"}],
    )).json()
    _, envelope = ask(client, "tresor", "payment-status", registry_body(PASSEPORT),
                      requester="BF/GOV/DIPF/PASSEPORTS", consent_id=consent["id"])
    assert envelope["data"] == {"paid": True}


@pytest.mark.parametrize(("case", "reason"), [
    ("sans accord", "Aucun accord du citoyen n'accompagne la demande"),
    ("accord inconnu", "Accord inconnu"),
    ("identifiant mal formé", "Accord inconnu"),
    ("accord retiré", "Accord retiré par le citoyen"),
    ("accord refusé", "Accord refusé par le citoyen"),
    ("accord expiré", "Accord expiré"),
    ("autre démarche", "L'accord ne couvre pas cette démarche"),
    ("autre demandeur", "Le demandeur n'est pas celui de l'accord"),
    ("sans demandeur", "Le demandeur n'est pas celui de l'accord"),
    ("autre personne", "La personne visée n'est pas celle de l'accord"),
    ("hors du périmètre", "L'accord ne couvre pas cette information"),
])
def test_nothing_leaves_without_a_matching_consent(client, app, journal, clock, granted, case, reason):
    app.state.guard._clients = {slug: Untouchable() for slug in app.state.guard.holders}
    consent_id, requester, body, service = granted["id"], FONCTION_PUBLIQUE, registry_body(), "is-adult"
    if case == "sans accord":
        consent_id = None
    elif case == "accord inconnu":
        consent_id = "00000000-0000-4000-8000-000000000000"
    elif case == "identifiant mal formé":
        consent_id = "pas-un-identifiant"
    elif case == "accord retiré":
        client.post(f"/v1/consents/{granted['id']}/revoke", headers=AUTH)
    elif case == "accord refusé":
        consent_id = client.post("/v1/consents", headers=AUTH, json=concours_consent(
            case_id="dossier-2", decision="refused", expires_at=None)).json()["id"]
    elif case == "accord expiré":
        clock.now += timedelta(days=31)
    elif case == "autre démarche":
        body = registry_body(PASSEPORT)
    elif case == "autre demandeur":
        requester = "BF/GOV/DIPF/PASSEPORTS"
    elif case == "sans demandeur":
        requester = None
    elif case == "autre personne":
        body = registry_body(pivot="ACTE:BOBO:1999:00042")
    elif case == "hors du périmètre":
        service = "identity"

    status, envelope = ask(client, "etat-civil", service, body, requester=requester, consent_id=consent_id)
    assert status == 200 and envelope["status"] == "refused" and envelope["data"] is None
    assert envelope["message"] == reason
    [refusal] = journal.search(event_type="holder_refusal")
    assert refusal["outcome"] == "refused" and refusal["purpose"] == reason
    assert refusal["holder_code"] == CIVIL and refusal["correlation_id"] == "requete-1"


def test_a_subsystem_of_the_requester_is_the_requester(client, granted):
    _, envelope = ask(client, "justice", "nationality", registry_body(),
                      requester=f"{FONCTION_PUBLIQUE}/RECRUTEMENT", consent_id=granted["id"])
    assert envelope["status"] == "ok" and envelope["data"] == {"burkinabe": True}


def test_a_registry_down_never_gives_yes(client, app, journal, granted):
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refusé", request=request)

    app.state.guard._clients["justice"] = httpx.Client(transport=httpx.MockTransport(down))
    _, envelope = ask(client, "justice", "nationality", registry_body(), consent_id=granted["id"])
    assert envelope["status"] == "unavailable" and envelope["data"] is None
    [event] = journal.search(event_type="holder_response")
    assert event["outcome"] == "unavailable" and event["data_categories"] is None


@pytest.mark.parametrize("reply", [
    httpx.Response(200, json={"status": "ok", "data": {"adult": "oui"}}),
    httpx.Response(200, json={"status": "ok", "data": {"age": 22}}),
    httpx.Response(200, json={"status": "peut-être"}),
    httpx.Response(200, text="pas du JSON"),
])
def test_an_answer_that_does_not_fit_the_rule_is_not_passed_on(client, app, granted, reply):
    app.state.guard._clients["etat-civil"] = httpx.Client(transport=httpx.MockTransport(lambda request: reply))
    _, envelope = ask(client, "etat-civil", "is-adult", registry_body(), consent_id=granted["id"])
    assert envelope["status"] == "unavailable" and envelope["data"] is None


def test_without_the_journal_no_data_leaves(client, journal, granted):
    journal.unavailable = True
    _, envelope = ask(client, "etat-civil", "is-adult", registry_body(), consent_id=granted["id"])
    assert envelope["status"] == "unavailable" and envelope["data"] is None
    assert envelope["message"].startswith("Journal de traçabilité indisponible")


def test_registry_statuses_pass_without_data_or_free_text(client, journal):
    consent = client.post("/v1/consents", headers=AUTH, json=concours_consent(subject_ref="ACTE:OUAGA:1990:99999")).json()
    _, envelope = ask(client, "etat-civil", "is-adult", registry_body(pivot="ACTE:OUAGA:1990:99999"), consent_id=consent["id"])
    assert envelope["status"] == "not_found" and envelope["data"] is None
    assert envelope["message"] == "Aucune fiche ne correspond"
    assert journal.search(event_type="holder_response")[0]["outcome"] == "not_found"


def test_the_citizen_checks_his_own_act_without_a_consent_record(client, journal):
    proof = {"request_id": "rattachement-1", "procedure": "citizen_identity_link", "parameters": {},
             "subject": {"pivot_id": AWA, "last_name": "KABORE", "first_names": "Awa",
                         "birth_date": "2004-03-12", "mother_name": "COMPAORE Salimata"}}
    _, envelope = ask(client, "etat-civil", "identity-match", proof, requester="BF/GOV/ONI/CNIB")
    assert envelope["status"] == "ok" and envelope["data"] == {"match": True}
    event = journal.search(event_type="holder_response")[0]
    assert event["consent_id"] is None and event["subject_ref"] == AWA and event["case_id"] is None
    assert "KABORE" not in json.dumps(event)

    _, refused = ask(client, "etat-civil", "identity-match", {**proof, "procedure": CONCOURS})
    assert refused["status"] == "refused"


def test_unknown_holder_service_or_malformed_body(client, granted):
    assert ask(client, "inconnu", "is-adult", registry_body(), consent_id=granted["id"])[0] == 404
    status, envelope = ask(client, "etat-civil", "date-de-naissance", registry_body(), consent_id=granted["id"])
    assert status == 404 and envelope["status"] == "invalid_request"
    status, envelope = ask(client, "etat-civil", "is-adult", registry_body(consent_id=granted["id"]),
                           consent_id=granted["id"])
    assert status == 400 and envelope["status"] == "invalid_request"


def test_the_rules_are_public(client):
    holders = {holder["slug"]: holder for holder in client.get("/holders").json()}
    assert set(holders) == {"etat-civil", "justice", "oni", "tresor", "transport", "police"}
    rules = {rule["service"]: rule for rule in holders["etat-civil"]["services"]}
    assert rules["identity"]["transmits"] == "fiche retrouvée : oui"
    assert rules["identity-match"]["basis"] == "citizen_request"
    assert holders["justice"]["organization"] == JUSTICE


def test_a_plugged_registry_answers_through_the_guard_without_restart(app, client, granted, tmp_path):
    """Épreuve « brancher le registre d'une autre équipe » : même garde, mêmes règles, autre registre."""
    from consent_service.holders import HolderCatalog
    from registries.civil_registry.app import create_app as create_civil

    from .conftest import TODAY

    ours, theirs = TestClient(create_civil(today=lambda: TODAY)), TestClient(create_civil(today=lambda: TODAY))
    calls = []

    def route(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        target = theirs if request.url.host == "equipe-b" else ours
        reply = target.request(request.method, request.url.path, content=request.content, headers=request.headers)
        return httpx.Response(reply.status_code, content=reply.content, headers=reply.headers)

    guard = app.state.guard
    guard._catalog, guard._static, guard._clients = HolderCatalog(overrides=tmp_path), None, {}
    guard._client = httpx.Client(transport=httpx.MockTransport(route))

    assert ask(client, "etat-civil", "is-adult", registry_body(), consent_id=granted["id"])[1]["data"] == {"adult": True}
    (tmp_path / "equipe-b.json").write_text('{"holders": {"etat-civil": {"registry_url": "http://equipe-b:8000"}}}')
    _, envelope = ask(client, "etat-civil", "is-adult", registry_body(request_id="r-2"), consent_id=granted["id"])
    assert envelope["data"] == {"adult": True}
    assert calls == ["civil-registry", "equipe-b"]
    view = {holder["slug"]: holder for holder in client.get("/holders").json()}["etat-civil"]
    assert view["registry_url"] == "http://equipe-b:8000" and view["origin"] == "equipe-b.json"
    assert view["services"][0]["reduction"] == {"keep": {"adult": "boolean"}}
