from datetime import date

from fastapi.testclient import TestClient

from registries.civil_registry.app import create_app

from .conftest import RESPONSE_SCHEMA, assert_conforms, call

AWA = "ACTE:OUAGA:2004:01234"


def test_identity_by_pivot_returns_only_title_fields(civil):
    body = call(civil, "identity", {"pivot_id": AWA}, procedure="cnib-application")
    assert body["status"] == "ok"
    assert body["request_id"] == "test-1"
    assert body["organization"] == "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
    assert body["data"] == {
        "pivot_id": AWA,
        "last_name": "KABORE",
        "first_names": "Awa",
        "sex": "F",
        "birth_date": "2004-03-12",
        "birth_place": "Ouagadougou",
        "birth_country": "BF",
        "born_in_burkina": True,
        "deceased": False,
    }


def test_identity_born_abroad(civil):
    body = call(civil, "identity", {"pivot_id": "ACTE:OUAGA:1998:00456"})
    assert body["data"]["born_in_burkina"] is False


def test_identity_unknown_pivot_is_not_found(civil):
    body = call(civil, "identity", {"pivot_id": "ACTE:OUAGA:2003:09999"})
    assert body["status"] == "not_found"
    assert body["data"] is None


def test_homonyms_born_same_day_are_ambiguous_without_candidates(civil):
    body = call(civil, "identity", {"last_name": "Traoré", "first_names": "Moussa", "birth_date": "1995-06-01"})
    assert body["status"] == "ambiguous"
    assert body["data"] is None
    assert "00321" not in str(body) and "00322" not in str(body)


def test_homonyms_are_distinguished_by_pivot(civil):
    body = call(civil, "identity", {"pivot_id": "ACTE:OUAGA:1995:00322"})
    assert body["status"] == "ok"


def test_same_name_different_birth_date_is_not_ambiguous(civil):
    body = call(civil, "identity", {"last_name": "KABORE", "first_names": "Awa", "birth_date": "1979-08-02"})
    assert body["status"] == "ok"
    assert body["data"]["pivot_id"] == "ACTE:OUAGA:1979:00412"


def test_spelling_without_accent_finds_accented_record(civil):
    body = call(civil, "identity", {"last_name": "ouedraogo", "first_names": "AMINATA", "birth_date": "1990-09-30"})
    assert body["status"] == "ok"
    assert body["data"]["pivot_id"] == "ACTE:OUAGA:1990:01502"


def test_deceased_person_is_flagged(civil):
    body = call(civil, "identity", {"pivot_id": "ACTE:OUAGA:1961:00087"})
    assert body["data"]["deceased"] is True


def test_is_adult_never_returns_birth_date(civil):
    body = call(civil, "is-adult", {"pivot_id": AWA})
    assert body["data"] == {"adult": True}


def test_minor_is_not_adult(civil):
    assert call(civil, "is-adult", {"pivot_id": "ACTE:OUAGA:2012:02210"})["data"] == {"adult": False}


def test_adult_in_a_few_days_switches_on_birthday():
    pivot = {"pivot_id": "ACTE:OUAGA:2008:03175"}
    before = TestClient(create_app(today=lambda: date(2026, 11, 18)))
    on_birthday = TestClient(create_app(today=lambda: date(2026, 11, 19)))
    assert call(before, "is-adult", pivot)["data"] == {"adult": False}
    assert call(on_birthday, "is-adult", pivot)["data"] == {"adult": True}


def test_born_on_29_february(civil):
    assert call(civil, "is-adult", {"pivot_id": "ACTE:OUAGA:2008:00560"})["data"] == {"adult": True}


def test_identity_match_answers_yes_or_no_only(civil):
    declared = {"pivot_id": AWA, "last_name": "Kaboré", "first_names": "Awa", "birth_date": "2004-03-12"}
    assert call(civil, "identity-match", declared)["data"] == {"match": True}
    wrong = {**declared, "birth_date": "2004-03-13"}
    assert call(civil, "identity-match", wrong)["data"] == {"match": False}


def test_identity_match_requires_pivot_and_criteria(civil):
    body = call(civil, "identity-match", {"pivot_id": AWA})
    assert body["status"] == "invalid_request"


def test_invalid_pivot_format_is_rejected_without_echoing_input(civil):
    response = civil.post("/services/identity", json={"subject": {"pivot_id": "KABORE-AWA-SECRET"}})
    assert response.status_code == 400
    body = response.json()
    assert_conforms(RESPONSE_SCHEMA, body)
    assert body["status"] == "invalid_request"
    assert "SECRET" not in body["message"]


def test_subject_without_identifier_is_rejected(civil):
    response = civil.post("/services/identity", json={"subject": {"last_name": "KABORE"}})
    assert response.status_code == 400
    assert response.json()["status"] == "invalid_request"


def test_unknown_service_is_404(civil):
    response = civil.post("/services/everything", json={"subject": {"pivot_id": AWA}})
    assert response.status_code == 404
    assert_conforms(RESPONSE_SCHEMA, response.json())


def test_malformed_json_is_rejected(civil):
    response = civil.post("/services/identity", content=b"{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json()["status"] == "invalid_request"


def test_health_and_service_list(civil):
    assert civil.get("/health").json()["status"] == "up"
    assert civil.get("/services").json()["services"] == ["identity", "identity-match", "is-adult"]
