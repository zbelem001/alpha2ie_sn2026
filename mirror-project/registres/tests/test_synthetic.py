from registries.common.synthetic import synthetic_records, BATCH
from registries.common.models import Subject

def test_hundred_citizens_are_consistent_across_three_registries():
    records = synthetic_records()
    assert set(records) == {"civil", "justice", "treasury"}
    for rows in records.values():
        assert len(rows) == 100
        assert len({row["pivot_id"] for row in rows}) == 100
        assert all(row["_seed_batch"] == BATCH for row in rows)
    for civil, justice, payment in zip(records["civil"], records["justice"], records["treasury"]):
        assert civil["pivot_id"] == justice["pivot_id"] == payment["pivot_id"]
        assert civil["birth_date"] == justice["birth_date"] == payment["birth_date"]
        Subject(pivot_id=civil["pivot_id"])

def test_references_are_distinct_and_scenarios_are_varied():
    rows = synthetic_records()
    for key, field in [("civil", "birth_act_number"), ("justice", "criminal_record_number"), ("justice", "nationality_reference"), ("treasury", "reference")]:
        assert len({row[field] for row in rows[key]}) == 100
    assert {r["burkinabe"] for r in rows["justice"]} == {True, False}
    assert {r["status"] for r in rows["treasury"]} == {"paid", "pending"}
    assert {r["convictions"] for r in rows["justice"]} == {0, 1}
