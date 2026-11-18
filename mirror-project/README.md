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
| [espace-usager/](espace-usager/README.md) | Espace usager | `frontend/`, partie citoyen | P1 | Branché sur Keycloak et l'API démarches (port 3000) | — (consomme l'API démarches) | build, lint, parcours dans Chrome |
| [guichet-agent/](guichet-agent/README.md) | Guichet agent (bonus) | `frontend/`, partie agent | P1 | Branché sur Keycloak et l'API démarches (port 3001) | — (consomme l'API démarches) | build, lint, parcours dans Chrome |
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

Interfaces : http://localhost:3000 (espace usager, compte `citoyen-demo` / `CitoyenDemo-2026!`) et http://localhost:3001 (guichet agent, compte `agent-demo` / `AgentDemo-2026!`).

Machine de 8 à 11 Go de mémoire : construire d'abord les deux interfaces l'une après l'autre (`docker compose build espace-usager && docker compose build guichet-agent`), puis `docker compose up -d`. Construites en parallèle avec le reste de la pile, elles ont fait tuer Docker Desktop par manque de mémoire (constaté le 18/11).

L'environnement d'origine se lance toujours depuis la racine du dépôt. Les deux utilisent les mêmes ports : arrêter l'un (`docker compose down`, dans son dossier) avant de lancer l'autre. Leurs conteneurs et volumes sont séparés (projets `dlnuf` et `dlnuf-couches`).

## Vérifié le 17 et le 18/11/2026

- Tests de chaque couche, chacune dans son propre environnement Python : registres 38, passerelle 72 (dont les tests d'interopérabilité avec les registres), démarches 28. Interfaces : construction et lint sans erreur.
- `docker compose up` : 11 services sains (contrôle de santé), Keycloak démarré, tâche `keycloak-profile-init` terminée sans erreur ; images des interfaces construites l'une après l'autre, 308 Mo chacune.
- Parcours par les routes des interfaces (23 contrôles) : connexion, cookies `httpOnly` sans jeton exposé, pages protégées, compte citoyen refusé au guichet et inversement, chaque interface ne relaie que ses routes, démarche à distance de bout en bout, déconnexion.
- Parcours dans les écrans, avec Chrome sans interface, sur les deux applications : démarche « concours direct » à distance (l'accord donné par Awa apparaît au guichet sans recharger, trois vérifications confirmées, consultations retrouvées dans l'espace usager), démarche au guichet avec le code simulé, profil, déconnexion ; aucune erreur dans la console.
- Démarche « passeport » (`agent-passeport-demo`) : cinq vérifications confirmées (ONI, état civil, Justice, Trésor) ; ouverture d'une démarche d'une autre administration refusée (403).
- Non vérifié : banc X-Road lancé depuis `passerelle/` (vérifié depuis `interoperability/`).

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

- **Keycloak** : realm de `main` conservé (celui de `feat/keycloak-realm` laissé de côté), avec deux corrections dans le miroir : portée `basic` (sans elle, pas de `sub` dans les jetons et le backend se rabattait sur `jti`, qui change à chaque jeton : le rattachement d'identité du citoyen était perdu à chaque connexion — même défaut sur `main`) et `KC_HOSTNAME` (un seul émetteur de jetons, que la connexion passe par le navigateur ou par un conteneur). **SMS** : Infobip dans la couche démarches, notifications simulées dans la passerelle (port 8107). À décider.
- **Valeurs de démonstration** dans `.env.example` du miroir (numéro fictif vérifié, clé de simulation des codes, clé de chiffrement des références) pour que `docker compose up` suffise. Données fictives uniquement ; hors démonstration, vraies clés dans `.env`.
- **Interfaces** : connexion par identifiant et mot de passe Keycloak (Direct Access Grant) pour garder le formulaire ; en production, flux Authorization Code avec PKCE. La saisie de références par le citoyen « pour une demande » n'existe pas dans l'API (références de l'agent ou du profil) ; le catalogue renvoie aussi les démarches d'autres administrations (refusées ensuite par l'API).
- **Un demandeur X-Road par démarche** : la couche démarches utilise un seul `XROAD_CLIENT_ID` ; en mode X-Road, la démarche passeport serait refusée.
- **Nom de registre** : la couche démarches interroge `BF/GOV/POLICE/DECLARATIONS`, alors que le registre s'appelle `BF/GOV/POLICE/PERTES` partout ailleurs.
- **Contrat de la couche démarches** (`demarches/openapi.yaml`, copie de `contracts/openapi/backend.yaml` à la racine) non valide : virgules non protégées lignes 71 et 291, `#/components/schemas/Error` non défini.
- **Démarrage sur une base neuve** : corrigé dans `backend/scripts/start.py` (et sa copie `demarches/scripts/start.py`), à relire par P2.
