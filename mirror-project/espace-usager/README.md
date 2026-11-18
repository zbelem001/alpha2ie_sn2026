# Couche espace usager

Couche obligatoire de la carte du jury. Responsable : Personne 1.

Application Next.js du citoyen, construite à partir d'une copie de `frontend/` (le dossier d'origine reste inchangé) et branchée sur Keycloak et l'API démarches. Le citoyen :

- rattache une fois son compte à son acte de naissance, avec une preuve vérifiée par l'état civil (nom, prénoms, date de naissance, nom de la mère ; jamais conservés) ;
- **lance lui-même une démarche**, sans guichet ni pièce à fournir : il choisit la démarche, voit les informations qui seront vérifiées, autorise ces vérifications, et le résultat arrive aussitôt (`POST /v1/citizen/cases`) ;
- répond aux demandes d'accord des administrations (démarches ouvertes au guichet, « à distance ») ;
- suit ses démarches et le résultat de chaque vérification (« Mes démarches ») ;
- **consulte et retire son accord** pour chaque démarche (quand, où, jusqu'à quand ; `DELETE /v1/cases/{id}/consent`) : aucune nouvelle vérification ne peut ensuite partir avec cet accord ;
- retrouve chaque consultation de ses informations, refus et blocages compris (« Historique des consultations », tiré du journal de traçabilité) ;
- **signale une consultation** depuis cet historique : « Je ne reconnais pas cette consultation » (contestation) ou « Une information est fausse : demander une correction » (`POST /v1/cases/{id}/journal/{consultation}/report`). Le signalement est inscrit au journal, l'administration qui a consulté le voit dans le dossier, et il reste affiché ;
- enregistre au besoin les références de ses documents (profil, chiffré par l'API).

## Lancer

Avec tout le miroir : `docker compose up -d --build` depuis `mirror-project/`, puis http://localhost:3000.

En développement (Keycloak et l'API démarches démarrés par le Compose du miroir) :

```bash
npm ci
npm run dev        # http://localhost:3000
npm run build && npm run lint
```

Compte de démonstration : `citoyen-demo` / `CitoyenDemo-2026!` (Awa, téléphone fictif 70 00 00 01). Rattachement : acte `ACTE:OUAGA:2004:01234`, KABORE Awa, née le 12/03/2004, mère : COMPAORE Salimata.

| Variable (serveur) | Défaut | Rôle |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | API démarches (`http://demarches:8000` dans Docker) |
| `KEYCLOAK_URL` | `http://localhost:8180` | Keycloak (`http://keycloak:8080` dans Docker) |
| `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` | `dlnuf`, `dlnuf-api` | Realm et client |

## Spécification et tests

- [openapi.yaml](openapi.yaml) : routes de l'application (connexion, session, déconnexion, relais vers l'API démarches avec la liste des routes relayées).
- Tests (Playwright, `npm ci` d'abord) :
  - `npm run test:unit` : logique sans navigateur (accord, consultations et signalements tirés du journal, routes relayées) ;
  - `npm run test:e2e` : parcours dans Chrome contre le miroir démarré (`docker compose up -d` dans `mirror-project/`) : pages protégées, refus d'un mauvais mot de passe et d'un compte agent, démarche faite par le citoyen seul puis consultations retrouvées (scénario de la vidéo), signalement d'une consultation, retrait de l'accord, déconnexion. Chrome installé est utilisé ; sinon `npx playwright install chromium` et `PLAYWRIGHT_CHANNEL=chromium`.

## Fonctionnement

- **Session côté serveur** (`src/lib/server/auth.ts`, `src/app/api/auth/*`) : l'identifiant et le mot de passe sont échangés contre des jetons Keycloak, gardés dans des cookies `httpOnly` et renouvelés automatiquement. Le navigateur ne voit jamais de jeton.
- **Relais** (`src/app/api/backend/[...path]`) : le navigateur appelle `/api/backend/…`, l'application ajoute le jeton et transmet à `/v1/…`. Seules les routes `cases`, `citizen`, `notifications` et `procedures` (catalogue) sont relayées (`src/lib/space.ts`).
- **Pages protégées** (`src/proxy.ts`) : sans session, `/usager` renvoie vers la connexion. L'API démarches vérifie de toute façon chaque jeton.
- **Journal** (`src/lib/journal.ts`) : l'état de l'accord, les consultations et les signalements sont tirés de `GET /v1/cases/{id}/journal` ; un signalement y est rattaché à sa consultation par `correlation_id`.
- La liste se rafraîchit toutes les 15 secondes : une demande ouverte au guichet apparaît sans recharger.

## Écarts avec `frontend/`

- Retirés (non demandés par la carte) : console d'administration locale, Centrale, inscription simulée, et toutes les simulations dans le navigateur (`localStorage`).
- Connexion : identifiant et mot de passe Keycloak au lieu du numéro de téléphone et du PIN simulés.
- **Références « pour cette demande »** : dans `frontend/`, le citoyen pouvait compléter les références d'une demande avant d'accorder. L'API démarches n'a pas de route pour cela : les références viennent de l'agent (à l'ouverture du dossier) ou du profil du citoyen. Pour un citoyen identifié par son acte (`ACTE:…`), les registres sont interrogés avec cet identifiant. À trancher entre P1 et P2 si cette saisie doit revenir.
- Accord au guichet : seul le code SMS vaut accord ; l'espace citoyen n'affiche alors qu'une information.

## Limites

- Connexion par échange identifiant / mot de passe (Direct Access Grant) pour garder le formulaire : en production, passer au flux Authorization Code avec PKCE.
- Un signalement est inscrit et visible, mais son traitement n'est pas outillé : pas d'état « traité », pas de réponse au citoyen, pas de transmission automatique au registre source (l'agent la fait).
