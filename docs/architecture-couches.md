# Architecture par couche (branche `mirror-project`)

La carte du jury impose un dossier par couche : registres, passerelle d'échange, consentement et minimisation, journal de traçabilité, espace usager (obligatoires), guichet agent et résilience (bonus). Chaque couche a sa spécification OpenAPI et ses tests.

**Principe retenu : on recopie, on ne déplace pas.** Sur `mirror-project`, les dossiers de couche sont construits à partir de copies. Les dossiers d'origine (`frontend/`, `backend/`, `interoperability/`) restent en place et inchangés, et `main` n'est pas touché. Si la nouvelle architecture est validée, elle remplace l'ancienne sur `main`.

## Les couches

| Dossier | Couche de la carte | Copié depuis | Responsable | État | OpenAPI | Tests |
|---|---|---|---|---|---|---|
| [registres/](../registres/README.md) | Registres | `interoperability/registries`, `mock_registry` | P3 | Fonctionne seul | [openapi.yaml](../registres/openapi.yaml), à remplacer par le contrat du jury | 36 |
| [passerelle/](../passerelle/README.md) | Passerelle d'échange | `interoperability/connectors`, `xroad`, `notifications` | P3 | Fonctionne seul | [openapi.yaml](../passerelle/openapi.yaml), [notifications](../passerelle/notifications.openapi.yaml) | 74 |
| [consentement-minimisation/](../consentement-minimisation/README.md) | Consentement et minimisation | À extraire de `demarches/app/api.py` | À désigner (P2 ?) | README seulement | — | — |
| [journal/](../journal/README.md) | Journal de traçabilité | À extraire de `demarches/app/api.py` | À désigner (P2 ?) | README seulement | — | — |
| [espace-usager/](../espace-usager/README.md) | Espace usager | `frontend/` (application entière) | P1 | Copie conforme | — | — |
| [guichet-agent/](../guichet-agent/README.md) | Guichet agent (bonus) | Dans `espace-usager/src/app/(agent)` | P1 | README seulement | — | — |
| [resilience/](../resilience/README.md) | Résilience (bonus) | Répartie (connecteurs, `execute_checks`, banc X-Road) | À désigner (P3 ?) | README seulement | — | — |
| [demarches/](../demarches/README.md) | (orchestration, hors carte) | `backend/` | P2 | Fonctionne | [openapi.yaml](../demarches/openapi.yaml), copie non valide de `contracts/openapi/backend.yaml` | 28 |

`infrastructure/` (PostgreSQL, Keycloak), `contracts/` et `docs/` restent communs.

## Lancer

```bash
docker compose -f compose.couches.yaml up -d --build                   # architecture par couche
docker compose -f compose.couches.yaml --profile xroad up -d --build   # avec le banc X-Road
```

`compose.yaml` (dossiers d'origine) reste inchangé. Les deux environnements utilisent les mêmes ports : arrêter l'un (`docker compose down` ou `docker compose -f compose.couches.yaml down`) avant de lancer l'autre. Leurs conteneurs et volumes sont séparés (projets `dlnuf` et `dlnuf-couches`).

## Vérifié le 17/11/2026 au soir

- Tests de chaque couche, chacune dans son propre environnement Python : registres 36, passerelle 74 (dont les tests d'interopérabilité avec les registres), démarches 28.
- `docker compose -f compose.couches.yaml up -d --build` sur des volumes neufs : les 11 services démarrent et sont sains ; base du backend créée au premier démarrage.
- Connexion Keycloak (`agent-demo`), `GET /v1/procedures` : 2 démarches ; sans jeton : 401.
- Depuis le conteneur `demarches`, connecteurs chargés depuis `passerelle/` : état civil `is-adult` → `ok`, ONI `cnib-status` → `ok`, SMS simulé → `sent`.
- Non vérifié : construction de `espace-usager/` (copie conforme de `frontend/`, non modifiée) ; banc X-Road lancé depuis `passerelle/`.

## Règles jusqu'à la bascule

- **`main` gelé** : uniquement des corrections urgentes. Toute correction faite dans un dossier d'origine doit être recopiée dans le dossier de couche correspondant.
- On travaille dans les dossiers de couche, sur `mirror-project` (ou des branches qui en partent).

## Critères pour basculer `main`

1. `docker compose up -d --build` lance l'architecture par couche en une commande.
2. Tous les tests passent.
3. Les démarches marchent de bout en bout.
4. Chaque couche obligatoire a son dossier, son `openapi.yaml` et ses tests.

Bascule : supprimer `frontend/`, `backend/` et `interoperability/`, renommer `compose.couches.yaml` en `compose.yaml` (et `docker-compose.couches.yml`), puis Pull Request de `mirror-project` vers `main`.

## Points à trancher ou à corriger

- **Keycloak** : realm de `main` conservé ; celui de `feat/keycloak-realm` laissé de côté. **SMS** : Infobip dans la couche démarches, notifications simulées dans la passerelle (port 8107). À décider.
- **Un demandeur X-Road par démarche** : la couche démarches utilise un seul `XROAD_CLIENT_ID` ; en mode X-Road, la démarche passeport serait refusée.
- **Nom de registre** : la couche démarches interroge `BF/GOV/POLICE/DECLARATIONS`, alors que le registre s'appelle `BF/GOV/POLICE/PERTES` partout ailleurs.
- **Contrat de la couche démarches** (`contracts/openapi/backend.yaml`) non valide : virgules non protégées lignes 71 et 291, `#/components/schemas/Error` non défini.
- **Démarrage sur une base neuve** : corrigé dans `backend/scripts/start.py` (et sa copie), à relire par P2.
