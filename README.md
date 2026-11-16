# Dites-le-nous une fois

Hackathon des universités 2026 · Finale · Sujet 02.

Socle d’interopérabilité administrative : vérifications ciblées, consentement, traçabilité et reprise après indisponibilité d’un registre. Les administrations obtiennent directement auprès des registres officiels les informations nécessaires à une démarche, au lieu de demander des pièces à l’usager.

## État du dépôt

| Lot | État |
|---|---|
| `interoperability/`, `infrastructure/` | Registres simulés, connecteurs et Docker Compose opérationnels (voir « Démarrer ») |
| `contracts/` | Contrat backend ↔ registres proposé (`registry-request`, `registry-response`), à valider ; autres schémas réservés |
| `frontend/`, `backend/` | Arborescence initiale, à initialiser |

Les fichiers `.gitkeep` permettent à Git de conserver les dossiers réservés.

## Responsabilités

| Dossier | Responsable | Contenu |
|---|---|---|
| `frontend/` | Personne 1 | Interfaces citoyenne et administrative, Next.js / TypeScript |
| `backend/` | Personne 2 | API FastAPI, consentements, orchestration, autorisations, audit |
| `interoperability/` | Personne 3 | X-Road, adaptateurs et registres simulés |
| `infrastructure/` | Personne 3 | Docker Compose, Keycloak et PostgreSQL |
| `contracts/` | Collectif | OpenAPI, schémas JSON et exemples partagés |
| `docs/` | Collectif | Architecture, API, modèle de données et installation |

## Démarrer

```bash
docker compose up -d --build
```

| Service | Adresse sur la machine |
|---|---|
| Registre d’état civil | http://localhost:8101/docs |
| Registre des transports | http://localhost:8102/docs |
| Justice (nationalité, casier) | http://localhost:8103/docs |
| Police (pertes) | http://localhost:8104/docs |
| Trésor (paiements, simulé) | http://localhost:8105/docs |
| Keycloak (comptes de démo : [infrastructure/keycloak/README.md](infrastructure/keycloak/README.md)) | http://localhost:8180 |
| PostgreSQL | localhost:55432 |

Pour changer les valeurs par défaut : `cp .env.example .env`, puis modifier `.env`.

## Contrat entre le backend et les registres

Le backend interroge un registre par :

```python
connector.query(organization="BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL", service="identity", payload={...})
```

- Requête (`payload`) : [contracts/schemas/registry-request.json](contracts/schemas/registry-request.json)
- Réponse : [contracts/schemas/registry-response.json](contracts/schemas/registry-response.json)
- Exemples : [contracts/examples/registry-exchanges.json](contracts/examples/registry-exchanges.json)

Statuts : `ok`, `not_found`, `ambiguous`, `refused`, `unavailable`, `invalid_request`. Seul `ok` porte des données. Le connecteur se choisit par `REGISTRY_CONNECTOR` (`direct`, puis `xroad`), sans modifier l’orchestrateur. Détails dans [interoperability/README.md](interoperability/README.md).

## Règles de travail

- Une branche par tâche, fusion dans `main` par Pull Request.
- Tout changement dans `contracts/` se décide ensemble.
- Chaque lot se teste seul, avec des mocks conformes aux contrats.
- X-Road ne doit pas bloquer le développement des interfaces ou du cœur métier.

## Documentation

- [Architecture et organisation](docs/architecture.md) : document de référence en cas de contradiction
- [Guide du projet](DITES-LE-NOUS-UNE-FOIS.md)
- [Interfaces prévues](interfaces%283%29.md)
- [Architecture avec X-Road](docs/architecture-xroad.md.pdf)
- [Variante : socle sans X-Road](docs/architecture-socle.md)
- [Contrats API](docs/api-documentation.md)
- [Modèle de données](docs/database-schema.md)
- [Installation](docs/installation.md)

## Licence

À choisir collectivement. `LICENSE` est un emplacement réservé et n’accorde pas de licence libre à ce stade.
