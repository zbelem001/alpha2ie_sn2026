"""Application lancée par uvicorn (configuration par variables d'environnement, voir le README de la couche)."""

from .app import create_app

app = create_app()
