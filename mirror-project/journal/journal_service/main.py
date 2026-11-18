"""Application lancée par uvicorn (configuration par variables d'environnement, voir journal/README.md)."""

from .app import create_app

app = create_app()
