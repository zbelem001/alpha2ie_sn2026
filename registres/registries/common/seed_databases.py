"""Provisionnement idempotent : conserve les fixtures et n'écrase aucune donnée existante."""
import json
import os
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb
from .synthetic import synthetic_records, BATCH

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {"civil": ROOT / "civil_registry/data/records.json", "justice": ROOT.parent / "mock_registry/justice/data/records.json", "treasury": ROOT.parent / "mock_registry/treasury/data/payments.json"}

def main():
    admin = os.environ["REGISTRY_ADMIN_DSN"]
    generated = synthetic_records()
    for name in ("civil", "justice", "treasury"):
        database, role = f"registry_{name}", f"registry_{name}_owner"
        password = os.environ[f"REGISTRY_{name.upper()}_PASSWORD"]
        with psycopg.connect(admin, autocommit=True) as connection:
            if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                connection.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            else:
                connection.execute(sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            if not connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
                connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(database), sql.Identifier(role)))
            connection.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        dsn = make_conninfo(admin, dbname=database, user=role, password=password)
        with psycopg.connect(dsn) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS registry_records (record_key text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now())")
            fixtures = json.loads(SOURCES[name].read_text(encoding="utf-8"))
            for index, record in enumerate(fixtures):
                key = record["reference"] if name == "treasury" else f"fixture:{index:04d}"
                if record.get("_seed_batch") == "complete-demo-10-v1":
                    connection.execute(
                        "INSERT INTO registry_records(record_key,data) VALUES (%s,%s) "
                        "ON CONFLICT(record_key) DO UPDATE SET data=excluded.data, updated_at=now() "
                        "WHERE registry_records.data->>'_seed_batch' = 'complete-demo-10-v1'",
                        (key, Jsonb(record)),
                    )
                else:
                    connection.execute("INSERT INTO registry_records(record_key,data) VALUES (%s,%s) ON CONFLICT DO NOTHING", (key, Jsonb(record)))
            for index, record in enumerate(generated[name], 1):
                key = record["reference"] if name == "treasury" else f"synthetic:{index:04d}"
                connection.execute("INSERT INTO registry_records(record_key,data) VALUES (%s,%s) ON CONFLICT DO NOTHING", (key, Jsonb(record)))
            count = connection.execute("SELECT count(*) FROM registry_records WHERE data->>'_seed_batch'=%s", (BATCH,)).fetchone()[0]
            total = connection.execute("SELECT count(*) FROM registry_records").fetchone()[0]
        print(f"{database}: {count} fiches fictives generees, {total} lignes au total (fixtures conservees)", flush=True)

if __name__ == "__main__":
    main()
