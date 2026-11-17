# Miroir : architecture par couche (branche `mirror-project`)

La carte du jury impose un dossier par couche : registres, passerelle d'échange, consentement et minimisation, journal de traçabilité, espace usager (obligatoires), guichet agent et résilience (bonus). Chaque couche a sa spécification OpenAPI et ses tests.

**Principe retenu : on recopie, on ne déplace pas.** Tout le miroir est dans ce dossier, construit à partir de copies, et se lance seul. À la racine du dépôt, l'organisation d'origine (`frontend/`, `backend/`, `interoperability/`, `infrastructure/`…) reste en place et inchangée, et `main` n'est pas touché. Si le miroir est validé, son contenu remplace l'ancienne organisation sur `main`.

## Contenu

| Dossier | Couche de la carte | Copié depuis (racine du dépôt) | Responsable | État | OpenAPI | Tests |
|---|---|---|---|---|---|---|
| [registres/](registres/README.md) | Registres | `interoperability/registries`, `mock_registry` | P3 | Fonctionne seul | [openapi.yaml](registres/openapi.yaml), à remplacer par le contrat du jury | 38 |
| [passerelle/](passerelle/README.md) | Passerelle d'échange | `interoperability/connectors`, `xroad`, `notifications` | P3 | Fonctionne seul | [openapi.yaml](passerelle/openapi.yaml), [notifications](passerelle/notifications.openapi.yaml) | 72 |
| [consentement-minimisation/](consentement-minimisation/README.md) | Consentement et minimisation | À extraire de `demarches/app/api.py` | À désigner (P2 ?) | README seulement | — | — |
| [journal/](journal/README.md) | Journal de traçabilité | À extraire de `demarches/app/api.py` | À désigner (P2 ?) | README seulement | — | — |
| [espace-usager/](espace-usager/README.md) | Espace usager | `frontend/` (application entière) | P1 | Copie conforme | — | — |
| [guichet-agent/](guichet-agent/README.md) | Guichet agent (bonus) | Dans `espace-usager/src/app/(agent)` | P1 | README seulement | — | — |
| [resilience/](resilience/README.md) | Résilience (bonus) | Répartie (connecteurs, `execute_checks`, banc X-Road) | À désigner (P3 ?) | README seulement | — | — |
| [demarches/](demarches/README.md) | (orchestration, hors carte) | `backend/` | P2 | Fonctionne | [openapi.yaml](demarches/openapi.yaml), copie non valide de `contracts/openapi/backend.yaml` | 28 |

Pas de dossier `contracts/` : chaque contrat est dans la couche qui en est responsable (`registres/schemas`, `passerelle/schemas`, `consentement-minimisation/schemas`, `demarches/schemas` et chaque `openapi.yaml`).

Également copiés depuis la racine, pour que le miroir soit complet : `infrastructure/` (PostgreSQL, realm Keycloak, Compose), `docs/` et `.env.example`.

## Lancer

Depuis ce dossier :

```bash
docker compose up -d --build                   # architecture par couche
docker compose --profile xroad up -d --build   # avec le banc X-Road
```

L'environnement d'origine se lance toujours depuis la racine du dépôt. Les deux utilisent les mêmes ports : arrêter l'un (`docker compose down`, dans son dossier) avant de lancer l'autre. Leurs conteneurs et volumes sont séparés (projets `dlnuf` et `dlnuf-couches`).

## Vérifié le 17/11/2026 au soir

- Tests de chaque couche, chacune dans son propre environnement Python : registres 38, passerelle 72 (dont les tests d'interopérabilité avec les registres), démarches 28.
- `docker compose up -d --build` : les 11 services démarrent et sont sains ; base de la couche démarches créée au premier démarrage.
- Connexion Keycloak (`agent-demo`), `GET /v1/procedures` : 2 démarches ; sans jeton : 401.
- Depuis le conteneur `demarches`, connecteurs chargés depuis `passerelle/` : état civil `is-adult` → `ok`, ONI `cnib-status` → `ok`, SMS simulé → `sent`.
- Non vérifié : construction de `espace-usager/` (copie conforme de `frontend/`, non modifiée) ; banc X-Road lancé depuis `passerelle/`.

## Règles jusqu'à la bascule

- **`main` gelé** : uniquement des corrections urgentes. Toute correction faite dans un dossier d'origine doit être recopiée dans le dossier correspondant du miroir.
- On travaille dans `mirror-project/`, sur la branche `mirror-project` (ou des branches qui en partent).

## Critères pour basculer `main`

1. `docker compose up -d --build` lance l'architecture par couche en une commande.
2. Tous les tests passent.
3. Les démarches marchent de bout en bout.
4. Chaque couche obligatoire a son dossier, son `openapi.yaml` et ses tests.

Bascule : remplacer le contenu de la racine du dépôt par celui de `mirror-project/` (suppression de `frontend/`, `backend/`, `interoperability/` et de l'ancien Compose), puis Pull Request de `mirror-project` vers `main`.

## Points à trancher ou à corriger

- **Keycloak** : realm de `main` conservé ; celui de `feat/keycloak-realm` laissé de côté. **SMS** : Infobip dans la couche démarches, notifications simulées dans la passerelle (port 8107). À décider.
- **Un demandeur X-Road par démarche** : la couche démarches utilise un seul `XROAD_CLIENT_ID` ; en mode X-Road, la démarche passeport serait refusée.
- **Nom de registre** : la couche démarches interroge `BF/GOV/POLICE/DECLARATIONS`, alors que le registre s'appelle `BF/GOV/POLICE/PERTES` partout ailleurs.
- **Contrat de la couche démarches** (`demarches/openapi.yaml`, copie de `contracts/openapi/backend.yaml` à la racine) non valide : virgules non protégées lignes 71 et 291, `#/components/schemas/Error` non défini.
- **Démarrage sur une base neuve** : corrigé dans `backend/scripts/start.py` (et sa copie `demarches/scripts/start.py`), à relire par P2.
