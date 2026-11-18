# Couche guichet agent

Couche bonus de la carte du jury. Responsable : Personne 1.

Application Next.js de l'agent, construite à partir d'une copie de `frontend/` (le dossier d'origine reste sur `main`, inchangé) et branchée sur Keycloak et l'API démarches. L'agent, sans demander aucune pièce :

- ouvre le dossier d'un citoyen pour une démarche de son administration (catalogue `GET /v1/procedures`) ;
- recueille l'accord : au guichet avec le code reçu par SMS (simulé), ou à distance depuis l'espace usager ;
- lance les vérifications et voit le résultat minimisé de chacune (« oui », « non », « indisponible », « à examiner ») ; un registre indisponible est réinterrogé automatiquement tant que l'accord est valide ;
- voit les **signalements du citoyen** : étiquette « Signalement » dans la liste (et le dossier sous le filtre « À reprendre ou examiner »), et dans le dossier, la vérification contestée (« le citoyen ne reconnaît pas la consultation », à examiner avant toute décision) ou la correction demandée, avec le registre à qui la transmettre.

## Lancer

Avec tout le miroir : `docker compose up -d --build` depuis `mirror-project/`, puis http://localhost:3001.

En développement (Keycloak et l'API démarches démarrés par le Compose du miroir) :

```bash
npm ci
npm run dev        # http://localhost:3001
npm run build && npm run lint
```

Comptes de démonstration : `agent-demo` / `AgentDemo-2026!` (Fonction publique, démarche « concours direct ») et `agent-passeport-demo` / `PassportDemo-2026!` (DIPF, démarche « passeport »). Citoyenne du parcours : Awa, téléphone 70 00 00 01 ; ses références de documents fictives sont `ACTE-DEMO-OUAGA-2004-01234`, `NAT-DEMO-OUAGA-2004-01234`, `CASIER-DEMO-OUAGA-2004-01234`, `CNIB-DEMO-OUAGA-2004-01234`, et `PAY-2026-0004` pour le timbre du passeport (le Trésor vérifie que le paiement correspond à la démarche).

Variables serveur : les mêmes que [l'espace usager](../espace-usager/README.md#lancer) ; `NEXT_PUBLIC_CITIZEN_SPACE_URL` (défaut `http://localhost:3000`, fixée à la construction) donne le lien vers l'espace usager.

## Spécification et tests

- [openapi.yaml](openapi.yaml) : routes de l'application (connexion, session, déconnexion, relais vers l'API démarches, limité à `procedures` et `cases`).
- Tests (Playwright, `npm ci` d'abord) :
  - `npm run test:unit` : routes relayées, accord et signalements tirés du journal ;
  - `npm run test:e2e` : parcours dans Chrome contre le miroir démarré : pages protégées, compte citoyen refusé, dossier au guichet sans pièce (accord par code simulé, vérifications, dossier retrouvé par la recherche), signalement du citoyen visible dans la liste et dans le dossier. Prérequis : compte d'Awa rattaché à son acte et une consultation signalée ; lancer d'abord `npm run test:e2e` dans `espace-usager/`, qui s'en charge.

## Fonctionnement

Même socle que l'espace usager : session côté serveur (cookies `httpOnly`), relais `/api/backend/…` limité ici aux routes `procedures` et `cases` (`src/lib/space.ts`), pages protégées par `src/proxy.ts`. L'état de l'accord et les signalements de chaque dossier sont tirés de son journal ; la liste se rafraîchit toutes les 10 secondes, pour voir arriver l'accord donné à distance.

## Écarts avec `frontend/`

- Retirés : espace citoyen (application `espace-usager/`), console d'administration locale, Centrale, simulations dans le navigateur.
- Les références de documents se saisissent à l'ouverture du dossier : l'API démarches n'a pas de route pour les modifier ensuite.
- Le catalogue renvoyé par l'API contient aussi les démarches d'autres administrations ; l'API refuse ensuite l'ouverture (message affiché). À filtrer côté API (P2).
