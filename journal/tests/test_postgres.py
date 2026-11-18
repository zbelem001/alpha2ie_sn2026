"""Contre un vrai PostgreSQL (facultatif) : verrou d'ajout seul et ajouts simultanés sans trou dans la chaîne.

Lancé seulement si JOURNAL_TEST_DATABASE_URL désigne une base jetable, par exemple, miroir démarré :
    JOURNAL_TEST_DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/journal_test python -m pytest
La base est créée si besoin, et sa table vidée au début (et à la fin) du test.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from journal_service.schemas import EventIn
from journal_service.start import ensure_database, install_schema
from journal_service.store import JournalStore

from .conftest import consultation

URL = os.environ.get("JOURNAL_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="JOURNAL_TEST_DATABASE_URL non défini")


@pytest.fixture
def store():
    ensure_database(URL, attempts=3)
    engine = create_engine(URL)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS journal_events"))
    install_schema(URL)
    yield JournalStore(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS journal_events"))
    engine.dispose()


def test_the_database_refuses_changes_and_removals(store):
    store.append(EventIn(**consultation()), source="demarches")
    for statement in ("UPDATE journal_events SET outcome = 'rejected'", "DELETE FROM journal_events",
                      "TRUNCATE journal_events"):
        with pytest.raises(DBAPIError, match="ajout seul"):
            with store._engine.begin() as connection:
                connection.execute(text(statement))
    assert store.verify().valid


def test_simultaneous_appends_keep_one_unbroken_chain(store):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda index: store.append(EventIn(**consultation(correlation_id=f"r-{index}")), source="demarches"),
                      range(40)))
    report = store.verify()
    assert report.valid and report.events == 40
