# Installation

Aucun secret réel ne doit être commité.

## Infrastructure et registres simulés (Personne 3)

Prérequis : Docker et Docker Compose.

```bash
docker compose up -d --build
```

Cette commande démarre PostgreSQL (port 55432), Keycloak (port 8180) et les six registres simulés (ports 8101 à 8106), dont le statut CNIB ONI sur le port 8106. Le détail est dans [infrastructure/README.md](../infrastructure/README.md).
Elle démarre aussi l’API FastAPI sur le port 8000, applique les migrations PostgreSQL et initialise le catalogue de démonstration.

Tests du lot interopérabilité :

```bash
cd interoperability
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Frontend (Personne 1)

À initialiser dans `frontend/` : Next.js, React, TypeScript, Tailwind.

## Backend (Personne 2)

Le backend FastAPI et ses dépendances sont construits dans Docker. L’API documentée est disponible à `http://localhost:8000/docs`. Le conteneur utilise les connecteurs du lot interopérabilité.
