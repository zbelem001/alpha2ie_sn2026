from .conftest import call

AWA = "ACTE:OUAGA:2004:01234"
ISSA = "ACTE:OUAGA:1998:00456"


# Transports ---------------------------------------------------------------------------


def test_valid_driving_licence(transport):
    body = call(transport, "driving-licence", {"pivot_id": AWA})
    assert body["data"] == {"valid": True, "categories": ["B"], "expires_on": "2034-05-01"}


def test_expired_driving_licence_reveals_nothing(transport):
    body = call(transport, "driving-licence", {"pivot_id": "ACTE:OUAGA:1995:00321"})
    assert body["data"] == {"valid": False, "categories": [], "expires_on": None}


def test_person_without_licence(transport):
    body = call(transport, "driving-licence", {"pivot_id": "ACTE:OUAGA:2001:01456"})
    assert body["status"] == "ok"
    assert body["data"]["valid"] is False


# Justice ------------------------------------------------------------------------------


def test_nationality_by_filiation(justice):
    assert call(justice, "nationality", {"pivot_id": ISSA})["data"] == {"burkinabe": True}


def test_acquired_nationality_does_not_reveal_how(justice):
    body = call(justice, "nationality", {"pivot_id": "ACTE:OUAGA:1985:00789"})
    assert body["data"] == {"burkinabe": True}


def test_registry_specific_document_identifiers_return_only_minimal_results(civil, justice, oni, treasury):
    cnib = call(
        oni,
        "cnib-status",
        {},
        parameters={"identifier_type": "cnib_number", "document_identifier": "CNIB-DEMO-OUAGA-2004-01234"},
    )
    birth_act = call(
        civil,
        "identity",
        {},
        parameters={"identifier_type": "birth_act_number", "document_identifier": "ACTE-DEMO-OUAGA-2004-01234"},
    )
    nationality = call(
        justice,
        "nationality",
        {},
        parameters={"identifier_type": "nationality_reference", "document_identifier": "NAT-DEMO-OUAGA-2004-01234"},
    )
    criminal_record = call(
        justice,
        "criminal-record-current",
        {},
        parameters={"identifier_type": "criminal_record_number", "document_identifier": "CASIER-DEMO-OUAGA-2004-01234"},
    )
    payment = call(
        treasury,
        "payment-status",
        {},
        procedure="passeport_ordinaire_precheck",
        parameters={"identifier_type": "payment_reference", "document_identifier": "PAY-2026-0004"},
    )

    assert cnib["data"] == {"valid": True}
    assert birth_act["data"] == {"found": True}
    assert nationality["data"] == {"burkinabe": True}
    assert criminal_record["data"] == {"valid": True}
    assert payment["data"] == {"paid": True}


def test_person_absent_from_justice_is_not_found_never_yes(justice):
    for service in ("nationality", "criminal-record"):
        body = call(justice, service, {"pivot_id": "ACTE:OUAGA:2000:00654"})
        assert body["status"] == "not_found"
        assert body["data"] is None


def test_criminal_record_with_conviction(justice):
    assert call(justice, "criminal-record", {"pivot_id": "ACTE:OUAGA:1992:01120"})["data"] == {"clean": False}
    assert call(justice, "criminal-record", {"pivot_id": AWA})["data"] == {"clean": True}


def test_justice_homonyms_are_ambiguous(justice):
    body = call(justice, "criminal-record", {"last_name": "TRAORE", "first_names": "Moussa", "birth_date": "1995-06-01"})
    assert body["status"] == "ambiguous"


# Police -------------------------------------------------------------------------------


def test_cnib_declared_lost(police):
    body = call(police, "loss-declaration", {"pivot_id": "ACTE:OUAGA:1997:00933"})
    assert body["data"] == {"declared": True, "reference": "PV-OUAGA-2026-004512", "declared_on": "2026-10-02"}


def test_other_document_lost_is_not_a_cnib_loss(police):
    pivot = {"pivot_id": "ACTE:OUAGA:1988:00230"}
    assert call(police, "loss-declaration", pivot)["data"]["declared"] is False
    passport = call(police, "loss-declaration", pivot, parameters={"document_type": "passeport"})
    assert passport["data"]["declared"] is True


def test_no_declaration(police):
    assert call(police, "loss-declaration", {"pivot_id": AWA})["data"]["declared"] is False


# Trésor -------------------------------------------------------------------------------


def test_payment_received(treasury):
    body = call(treasury, "payment-status", {"pivot_id": AWA}, procedure="cnib-application")
    assert body["data"] == {"paid": True, "reference": "PAY-2026-0001", "amount_xof": 2500}


def test_payment_pending_then_confirmed(treasury):
    pending = call(treasury, "payment-status", {"pivot_id": ISSA}, procedure="cnib-application")
    assert pending["data"]["paid"] is False
    assert treasury.post(f"/simulate/payments/{pending['data']['reference']}/pay").status_code == 200
    assert call(treasury, "payment-status", {"pivot_id": ISSA}, procedure="cnib-application")["data"]["paid"] is True


def test_new_test_payment(treasury):
    pivot = "ACTE:OUAGA:2001:01456"
    assert call(treasury, "payment-status", {"pivot_id": pivot}, procedure="cnib-application")["data"]["paid"] is False
    created = treasury.post(
        "/simulate/payments", json={"pivot_id": pivot, "procedure": "cnib-application", "amount_xof": 2500}
    )
    assert created.status_code == 201
    assert call(treasury, "payment-status", {"pivot_id": pivot}, procedure="cnib-application")["data"]["paid"] is True


def test_payment_status_requires_procedure(treasury):
    assert call(treasury, "payment-status", {"pivot_id": AWA})["status"] == "invalid_request"


def test_treasury_state_is_not_shared_between_instances():
    from fastapi.testclient import TestClient

    from mock_registry.treasury.app import create_app

    first, second = TestClient(create_app()), TestClient(create_app())
    first.post("/simulate/payments/PAY-2026-0002/pay")
    body = call(second, "payment-status", {"pivot_id": ISSA}, procedure="cnib-application")
    assert body["data"]["paid"] is False
