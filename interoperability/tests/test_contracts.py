"""Les exemples publiés dans contracts/examples restent conformes aux schémas."""

import json

from .conftest import CONTRACTS, REQUEST_SCHEMA, RESPONSE_SCHEMA, assert_conforms


def test_published_examples_match_schemas():
    examples = json.loads((CONTRACTS / "examples" / "registry-exchanges.json").read_text(encoding="utf-8"))
    assert examples["examples"]
    for example in examples["examples"]:
        assert_conforms(REQUEST_SCHEMA, example["payload"])
        assert_conforms(RESPONSE_SCHEMA, example["response"])
        assert example["response"]["organization"] == example["organization"]
        assert example["response"]["service"] == example["service"]


def test_schema_forbids_data_outside_ok():
    leaking = {
        "request_id": None,
        "organization": "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
        "service": "identity",
        "status": "ambiguous",
        "data": {"candidates": []},
        "message": None,
        "responded_at": "2026-11-16T10:00:00Z",
    }
    assert list(RESPONSE_SCHEMA.iter_errors(leaking))
