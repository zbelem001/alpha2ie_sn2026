"""Démarrage en conteneur : attendre PostgreSQL, créer la base des accords si elle manque
(volume créé avant cette couche), vérifier le fichier des détenteurs, puis lancer l'API."""

from __future__ import annotations

import os
import time

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from .holders import load_holders
from .models import Base


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


def main() -> None:
    holders = load_holders()
    print(f"Détenteurs servis : {', '.join(sorted(holders))}", flush=True)
    url = os.environ["DATABASE_URL"]
    ensure_database(url)
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    os.execvp("uvicorn", ["uvicorn", "consent_service.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
