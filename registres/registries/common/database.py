"""Stockage local à chaque registre. Une connexion n'accède qu'à sa propre base."""
from collections.abc import Sequence
from typing import Any

class DatabaseRecords(Sequence):
    def __init__(self, dsn: str):
        self.dsn = dsn

    def __iter__(self):
        import psycopg
        with psycopg.connect(self.dsn, connect_timeout=3) as connection:
            rows = connection.execute("SELECT data FROM registry_records ORDER BY record_key").fetchall()
        return iter(row[0] for row in rows)

    def __len__(self):
        import psycopg
        with psycopg.connect(self.dsn, connect_timeout=3) as connection:
            return connection.execute("SELECT count(*) FROM registry_records").fetchone()[0]

    def __getitem__(self, index):
        return list(iter(self))[index]

    def save(self, record: dict[str, Any]):
        import psycopg
        from psycopg.types.json import Jsonb
        with psycopg.connect(self.dsn, connect_timeout=3) as connection:
            connection.execute("INSERT INTO registry_records(record_key,data) VALUES (%s,%s) ON CONFLICT(record_key) DO UPDATE SET data=excluded.data, updated_at=now()", (record["reference"], Jsonb(record)))

    def append(self, record):
        self.save(record)

    def ping(self):
        import psycopg
        with psycopg.connect(self.dsn, connect_timeout=3) as connection:
            connection.execute("SELECT 1 FROM registry_records LIMIT 1")
