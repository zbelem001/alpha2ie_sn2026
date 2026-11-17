"""Wait for PostgreSQL, migrate, seed demo catalog, then run FastAPI."""
import os
import subprocess
import sys
import time

import psycopg
from psycopg import OperationalError


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

    subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "scripts.seed_demo"], check=True)
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
