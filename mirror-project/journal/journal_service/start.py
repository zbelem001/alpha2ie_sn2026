"""Démarrage en conteneur : attendre PostgreSQL, créer la base du journal si elle manque
(volume créé avant cette couche), la table et le verrou d'ajout seul, puis lancer l'API."""

from __future__ import annotations

import os
import time

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from .models import Base

# Ajout seul, imposé par la base elle-même : ni modification, ni suppression, ni vidage,
# même par le service. La chaîne d'empreintes rend visible ce qui contournerait ce verrou.
APPEND_ONLY = (
    """
    CREATE OR REPLACE FUNCTION journal_events_append_only() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'journal_events : ajout seul, ni modification ni suppression';
    END;
    $$
    """,
    "DROP TRIGGER IF EXISTS journal_events_no_change ON journal_events",
    "CREATE TRIGGER journal_events_no_change BEFORE UPDATE OR DELETE ON journal_events "
    "FOR EACH ROW EXECUTE FUNCTION journal_events_append_only()",
    "DROP TRIGGER IF EXISTS journal_events_no_truncate ON journal_events",
    "CREATE TRIGGER journal_events_no_truncate BEFORE TRUNCATE ON journal_events "
    "FOR EACH STATEMENT EXECUTE FUNCTION journal_events_append_only()",
)


def ensure_database(url: str, attempts: int = 60) -> None:
    target = make_url(url)
    maintenance = target.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    for attempt in range(1, attempts + 1):
        try:
            connection = psycopg.connect(maintenance, autocommit=True, connect_timeout=3)
            break
        except psycopg.OperationalError as exc:
            print(f"PostgreSQL pas encore prêt ({attempt}/{attempts}) : {exc}", flush=True)
            time.sleep(1)
    else:
        raise SystemExit(f"PostgreSQL inaccessible après {attempts} tentatives")
    with connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target.database,)).fetchone()
        if not exists:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target.database)))
            print(f"Base « {target.database} » créée.", flush=True)


def install_schema(url: str) -> None:
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for statement in APPEND_ONLY:
            connection.execute(text(statement))
    engine.dispose()


def main() -> None:
    url = os.environ["DATABASE_URL"]
    ensure_database(url)
    install_schema(url)
    os.execvp("uvicorn", ["uvicorn", "journal_service.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
