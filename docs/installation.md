# Installation

Aucun secret réel ne doit être commité.

## Infrastructure et registres simulés (Personne 3)

Prérequis : Docker et Docker Compose.

```bash
docker compose up -d --build
```

Cette commande démarre PostgreSQL (port 55432), Keycloak (port 8180), les cinq registres simulés (ports 8101 à 8105) et le service de notifications simulé (port 8106). Le détail est dans [infrastructure/README.md](../infrastructure/README.md).

Tests du lot interopérabilité :

```bash
cd interoperability
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Frontend (Personne 1)

À initialiser dans `frontend/` : Next.js, React, TypeScript, Tailwind.

## Backend (Personne 2)

À initialiser dans `backend/` : FastAPI et les dépendances Python. Pour interroger les registres et envoyer les SMS ou e-mails simulés, utiliser les connecteurs du lot interopérabilité (`pip install -e ../interoperability`) : `build_connector()` et `build_notifier()`, décrits dans [interoperability/README.md](../interoperability/README.md).
