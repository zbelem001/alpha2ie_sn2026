"""Wait for PostgreSQL, migrate, seed demo catalog, then run FastAPI."""
import os
import subprocess
import sys
import time

import psycopg
from psycopg import OperationalError


def database_is_empty(url: str) -> bool:
    with psycopg.connect(url, connect_timeout=3) as connection:
        row = connection.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchone()
    return row[0] == 0


def create_fresh_schema() -> None:
    """Create the current schema on an empty database, then mark it as migrated.

    Revision 0001 builds its tables from the current models, so replaying
    0002+ on an empty database re-adds columns that already exist
    (DuplicateColumn on registry_requests.lookup_identifier_type). Existing
    databases keep using `alembic upgrade head`.
    """
    from sqlalchemy import create_engine

    from app.database import models  # noqa: F401 - populate Base.metadata
    from app.database.base import Base

    print("Base vide : création du schéma actuel, puis alembic stamp head.", flush=True)
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(engine)
    engine.dispose()
    subprocess.run(["alembic", "stamp", "head"], check=True)


def main() -> None:
    # SQLAlchemy's URL includes a driver suffix that libpq does not accept.
    url = os.environ["DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    for attempt in range(1, 61):
        try:
            with psycopg.connect(url, connect_timeout=3):
                break
        except OperationalError as exc:
            print(f"PostgreSQL pas encore prêt ({attempt}/60): {exc}", flush=True)
            time.sleep(1)
    else:
        raise SystemExit("PostgreSQL inaccessible après 60 tentatives")

    if database_is_empty(url):
        create_fresh_schema()
    else:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "scripts.seed_demo"], check=True)
    subprocess.run([sys.executable, "-m", "scripts.seed_administration_catalog"], check=True)
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
