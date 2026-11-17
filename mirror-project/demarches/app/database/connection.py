import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend",
    )


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """Dépendance FastAPI : fournit une session et la ferme après la requête."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
