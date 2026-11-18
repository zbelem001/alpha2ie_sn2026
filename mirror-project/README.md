# Miroir : architecture par couche (branche `mirror-project`)

La carte du jury impose un dossier par couche : registres, passerelle d'échange, consentement et minimisation, journal de traçabilité, espace usager (obligatoires), guichet agent et résilience (bonus). Chaque couche a sa spécification OpenAPI et ses tests.

**Principe retenu : on recopie, on ne déplace pas.** Tout le miroir est dans ce dossier, construit à partir de copies, et se lance seul. L'organisation d'origine (`frontend/`, `backend/`, `interoperability/`, `infrastructure/`…) reste sur `main`, qui n'est pas touché ; depuis le 18/11, cette branche ne la contient plus, pour ne pas avoir chaque fichier en double. Si le miroir est validé, son contenu remplace l'ancienne organisation sur `main`.

## Contenu

| Dossier | Couche de la carte | Copié depuis (`main`) | Responsable | État | OpenAPI | Tests |
|---|---|---|---|---|---|---|
| [registres/](registres/README.md) | Registres | `interoperability/registries`, `mock_registry` | P3 | Fonctionne seul | [openapi.yaml](registres/openapi.yaml), à remplacer par le contrat du jury | 43 |
| [passerelle/](passerelle/README.md) | Passerelle d'échange | `interoperability/connectors`, `xroad`, `notifications` | P3 | Fonctionne seul ; joint chaque détenteur par la garde de la couche consentement-minimisation | [openapi.yaml](passerelle/openapi.yaml), [notifications](passerelle/notifications.openapi.yaml) | 74 |
| [consentement-minimisation/](consentement-minimisation/README.md) | Consentement et minimisation | Extrait de `demarches/app/api.py` (18/11) | À désigner (P2 ?) | Service à part (port 8109) : registre des accords, et garde devant chaque registre (accord vérifié, réponse réduite, journal) | [openapi.yaml](consentement-minimisation/openapi.yaml), [schemas/consent.json](consentement-minimisation/schemas/consent.json) | 58 |
| [journal/](journal/README.md) | Journal de traçabilité | Extrait de `demarches/app/api.py` (18/11) | À désigner (P2 ?) | Service à part (port 8108), écrit et lu par la couche démarches | [openapi.yaml](journal/openapi.yaml) | 33, et 2 contre PostgreSQL |
| [espace-usager/](espace-usager/README.md) | Espace usager | `frontend/`, partie citoyen | P1 | Branché sur Keycloak et l'API démarches (port 3000) | [openapi.yaml](espace-usager/openapi.yaml) (routes de l'application) | Playwright : 10 unitaires, 7 de bout en bout |
| [guichet-agent/](guichet-agent/README.md) | Guichet agent (bonus) | `frontend/`, partie agent | P1 | Branché sur Keycloak et l'API démarches (port 3001) | [openapi.yaml](guichet-agent/openapi.yaml) (routes de l'application) | Playwright : 5 unitaires, 4 de bout en bout |
| [resilience/](resilience/README.md) | Résilience (bonus) | Répartie (connecteurs, garde, `_run_checks`, banc X-Road) | P3 | Reprise automatique côté serveur (`demarches/app/retry.py`), répétition de l'épreuve sur la pile (`scenarios/`) | — (pas de service propre) | 7, de bout en bout |
| [demarches/](demarches/README.md) | (orchestration, hors carte) | `backend/` | P2 | Fonctionne | [openapi.yaml](demarches/openapi.yaml), issu de `contracts/openapi/backend.yaml`, corrigé et complété | 43 |

Pas de dossier `contracts/` : chaque contrat est dans la couche qui en est responsable (`registres/schemas`, `passerelle/schemas`, `consentement-minimisation/schemas`, `demarches/schemas` et chaque `openapi.yaml`).

Également copiés depuis `main`, pour que le miroir soit complet : `infrastructure/` (PostgreSQL, realm Keycloak, Compose), `docs/` et `.env.example`.

## Lancer

Depuis ce dossier :

```bash
docker compose up -d --build                   # architecture par couche
docker compose --profile xroad up -d --build   # avec le banc X-Road
```

Interfaces : http://localhost:3000 (espace usager, compte `citoyen-demo` / `CitoyenDemo-2026!`) et http://localhost:3001 (guichet agent, compte `agent-demo` / `AgentDemo-2026!`).

Machine de 8 à 11 Go de mémoire : construire d'abord les deux interfaces l'une après l'autre (`docker compose build espace-usager && docker compose build guichet-agent`), puis `docker compose up -d`. Construites en parallèle avec le reste de la pile, elles ont fait tuer Docker Desktop par manque de mémoire (constaté le 18/11).

L'environnement d'origine se lance depuis la branche `main` (`git checkout main`, puis `docker compose up -d --build` à la racine). Les deux utilisent les mêmes ports : arrêter l'un (`docker compose down`, dans son dossier) avant de lancer l'autre. Leurs conteneurs et volumes sont séparés (projets `dlnuf` et `dlnuf-couches`).

## Vérifié le 17 et le 18/11/2026

- Tests de chaque couche, chacune dans son propre environnement Python : registres 43, passerelle 74 (dont les tests d'interopérabilité avec les registres), consentement-minimisation 58 (dont connecteur → garde → registres simulés), journal 33 (et 2 contre PostgreSQL), démarches 43, résilience 7 (toute la chaîne, registres débranchés). Interfaces : construction et lint sans erreur. Les sept `openapi.yaml` passent `openapi-spec-validator` ; celui de `demarches/` couvre toutes les routes de l'API.
- `docker compose up` : 13 services sains (contrôle de santé), Keycloak démarré, tâche `keycloak-profile-init` terminée sans erreur ; images des interfaces construites l'une après l'autre, 308 Mo chacune.
- Couche journal (18/11) : base `journal` créée au démarrage sur le volume existant ; tests de bout en bout des deux interfaces passés (7 et 4) avec le journal à part ; consultations d'Awa retrouvées par citoyen avec le jeton auditeur (`GET /v1/events`), chaîne d'empreintes intacte, accès refusé sans jeton (401) ; déclencheur d'ajout seul et ajouts simultanés vérifiés contre PostgreSQL.
- Couche consentement-minimisation (18/11) : base `consentement` créée au démarrage ; tests de bout en bout des deux interfaces passés (7 et 4, un seul navigateur à la fois faute de mémoire) avec chaque vérification passée par la garde ; démarche passeport par l'API : cinq vérifications confirmées, et pour chacune, au journal, ce qui est sorti de chez le détenteur (`holder_response` : « burkinabè », « fiche retrouvée », « payé », « valide ») et le résultat côté demandeur (`registry_check`), reliés par l'identifiant de la requête ; demande sans accord refusée par la garde et inscrite au journal (`holder_refusal`) ; chaîne d'empreintes intacte.
- Parcours par les routes des interfaces (23 contrôles) : connexion, cookies `httpOnly` sans jeton exposé, pages protégées, compte citoyen refusé au guichet et inversement, chaque interface ne relaie que ses routes, démarche à distance de bout en bout, déconnexion.
- Parcours dans les écrans, avec Chrome sans interface, sur les deux applications : démarche « concours direct » à distance (l'accord donné par Awa apparaît au guichet sans recharger, trois vérifications confirmées, consultations retrouvées dans l'espace usager), démarche au guichet avec le code simulé, profil, déconnexion ; aucune erreur dans la console.
- Retrait de l'accord par le citoyen dans « Mes démarches » : état « retiré » affiché, second retrait refusé par l'API, retrait inscrit au journal (Chrome).
- Démarche lancée par le citoyen seul, depuis l'espace usager (sans guichet, couche bonus) : choix de la démarche, accord, trois vérifications confirmées, résultat et consultations visibles aussitôt (Chrome).
- Signalement d'une consultation par le citoyen (« Je ne reconnais pas cette consultation » ou demande de correction) : inscrit au journal, toujours affiché après rechargement, visible au guichet (étiquette « Signalement » dans la liste, détail dans le dossier) ; second signalement identique refusé, signalement par un autre citoyen ou d'un événement qui n'est pas une consultation refusé (Chrome et tests de l'API).
- Démarche « passeport » (`agent-passeport-demo`) : cinq vérifications confirmées (ONI, état civil, Justice, Trésor) ; ouverture d'une démarche d'une autre administration refusée (403).
- Sécurité : le casier d'un tiers saisi pour Awa donne « introuvable » au lieu de lui être attribué ; le rattachement d'un acte exige la preuve de titularité (refus identique pour une preuve fausse et un acte inexistant, homonyme refusé, essais limités), testé aussi dans Chrome.
- Charte graphique ([docs/charte-graphique.md](docs/charte-graphique.md)) : l'esprit de `DESIGN.md` avec les couleurs des armoiries, sur les deux interfaces. Tests de bout en bout passés, aucune page ne déborde en largeur (390 et 1 366 px), audit axe-core WCAG 2.1 A et AA sans violation ; contrastes sur les surfaces givrées calculés à la main.
- Non vérifié : banc X-Road lancé depuis `passerelle/` (vérifié depuis `interoperability/`).

## Règles jusqu'à la bascule

- **`main` gelé** : uniquement des corrections urgentes. Toute correction faite dans un dossier d'origine doit être recopiée dans le dossier correspondant du miroir : cette branche ne contenant plus les dossiers d'origine, elle se recopie à la main et ne se fusionne pas.
- On travaille dans `mirror-project/`, sur la branche `mirror-project` (ou des branches qui en partent).

## Critères pour basculer `main`

1. `docker compose up -d --build` lance l'architecture par couche en une commande.
2. Tous les tests passent.
3. Les démarches marchent de bout en bout.
4. Chaque couche obligatoire a son dossier, son `openapi.yaml` et ses tests.

Bascule : les dossiers d'origine sont déjà retirés de cette branche ; remonter le contenu de `mirror-project/` à la racine, puis Pull Request de `mirror-project` vers `main`, qui y supprimera `frontend/`, `backend/`, `interoperability/`, `contracts/` et l'ancien Compose.

## Points à trancher ou à corriger

- **Keycloak** : realm de `main` conservé (celui de `feat/keycloak-realm` laissé de côté), avec trois corrections dans le miroir : portée `basic` (sans elle, pas de `sub` dans les jetons et le backend se rabattait sur `jti`, qui change à chaque jeton : le rattachement d'identité du citoyen était perdu à chaque connexion — même défaut sur `main`), `KC_HOSTNAME` (un seul émetteur de jetons, que la connexion passe par le navigateur ou par un conteneur) et `sslRequired: none` sur les realms `master` et `dlnuf` (18/11 : avec la valeur par défaut `external`, Keycloak refusait en HTTP les jetons demandés depuis la machine à travers Docker Desktop, « HTTPS required » : console d'administration et `npm run dev` bloqués). Ce dernier réglage est réappliqué à chaque `docker compose up` par `keycloak-profile-init` (`KEYCLOAK_SSL_REQUIRED`, `.env.example`) ; il ne vaut que pour la démonstration en HTTP : derrière HTTPS, `external` ou `all`. **SMS** : Infobip dans la couche démarches, notifications simulées dans la passerelle (port 8107). À décider.
- **Sécurité des données** ([docs/resolution-des-donnees.md](docs/resolution-des-donnees.md), §11) : corrigés dans le miroir, le rattachement d'identité sans preuve de titularité (§11.1 : nom de la mère vérifié par l'état civil, essais limités) et la référence de pièce non rapprochée de la personne (§11.2 : le casier d'un tiers n'est plus attribué). Restent ouverts : les comptes sans acte rattaché (§11.3) et la liste des références conservée par la plateforme (§11.4).
- **Valeurs de démonstration** dans `.env.example` du miroir (numéro fictif vérifié, clé de simulation des codes, clé de chiffrement des références) pour que `docker compose up` suffise. Données fictives uniquement ; hors démonstration, vraies clés dans `.env`.
- **Interfaces** : connexion par identifiant et mot de passe Keycloak (Direct Access Grant) pour garder le formulaire ; en production, flux Authorization Code avec PKCE. La saisie de références par le citoyen « pour une demande » n'existe pas dans l'API (références de l'agent ou du profil) ; le catalogue renvoie aussi les démarches d'autres administrations (refusées ensuite par l'API).
- **Demandeurs X-Road** : chaque vérification part avec l'administration du dossier (traduite par `XROAD_CLIENTS`). Restent, sur le banc X-Road : déclarer un sous-système pour la DIPF (sinon la démarche passeport est refusée en mode X-Road) et faire pointer les fournisseurs sur la garde de la couche consentement-minimisation (sinon les appels X-Road la contournent).
- **Nom de registre** : la couche démarches interroge `BF/GOV/POLICE/DECLARATIONS`, alors que le registre s'appelle `BF/GOV/POLICE/PERTES` partout ailleurs.
- **Contrat de la couche démarches** (`demarches/openapi.yaml`, copie de `contracts/openapi/backend.yaml` à la racine) non valide : virgules non protégées lignes 71 et 291, `#/components/schemas/Error` non défini.
- **Démarrage sur une base neuve** : corrigé dans `backend/scripts/start.py` (et sa copie `demarches/scripts/start.py`), à relire par P2.
