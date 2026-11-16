# Dites-le-nous une fois

Socle d’interopérabilité administrative : vérifications ciblées, consentement, traçabilité et reprise après indisponibilité d’un registre.

## État du dépôt

Arborescence initiale conforme au document d’organisation. Les applications, contrats métier et services ne sont pas encore implémentés. Aucun lancement applicatif n’est disponible à ce stade. Les fichiers `.gitkeep` permettent à Git de conserver les dossiers réservés.

## Responsabilités

| Dossier | Responsable | Contenu |
|---|---|---|
| `frontend/` | Personne 1 | Interfaces citoyenne et administrative, Next.js / TypeScript |
| `backend/` | Personne 2 | API FastAPI, consentements, orchestration, autorisations, audit |
| `interoperability/` | Personne 3 | X-Road, adaptateurs et registres simulés |
| `infrastructure/` | Personne 3 | Docker Compose, Keycloak et PostgreSQL |
| `contracts/` | Collectif | OpenAPI, schémas JSON et exemples partagés |
| `docs/` | Collectif | Architecture, API, modèle de données et installation |

## Premières étapes

1. Valider les contrats et statuts métier dans `contracts/`.
2. Initialiser le frontend et le backend dans leurs dossiers respectifs.
3. Développer avec des mocks conformes aux contrats partagés.
4. Configurer les registres simulés et l’environnement Docker Compose.
5. Intégrer progressivement puis tester le parcours complet.

Les changements passent par des branches de travail et des Pull Requests. X-Road ne doit pas bloquer le développement des interfaces ou du cœur métier.

## Documentation

- [Architecture et organisation](docs/architecture.md)
- [Guide du projet](DITES-LE-NOUS-UNE-FOIS.md)
- [Interfaces prévues](interfaces%283%29.md)
- [Contrats API](docs/api-documentation.md)
- [Modèle de données](docs/database-schema.md)
- [Installation](docs/installation.md)

## Licence

À choisir collectivement. `LICENSE` est un emplacement réservé et n’accorde pas de licence libre à ce stade.
