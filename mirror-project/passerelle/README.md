# Couche passerelle d'échange

Responsable : Personne 3. Couche obligatoire de la carte du jury.

Copie de `interoperability/connectors`, `interoperability/xroad` et `interoperability/notifications` (branche `mirror-project`). Les dossiers d'origine restent en place.

## Contenu

| Dossier | Rôle |
|---|---|
| `connectors/` | Connecteurs utilisés par la couche démarches : `build_connector()` (mode `direct` ou `xroad`) et `build_notifier()`. Ne lèvent jamais d'exception : statuts `ok`, `not_found`, `ambiguous`, `refused`, `unavailable`, `invalid_request`. |
| `xroad/` | Banc X-Road 7.8.3 (serveur central, autorité de test, deux Security Servers) et sa configuration automatique. Détails : [xroad/README.md](xroad/README.md). |
| `notifications/` | SMS et e-mails simulés (port 8107) : boîte d'envoi, téléphone du citoyen, réponses. |

Le paquet installé par la couche démarches (`pip install -e ../passerelle`) ne dépend que de `httpx` et `PyYAML`. La passerelle ne dépend pas de la couche registres.

## Routage et en-têtes

- **Connecteur direct** : table identifiant X-Road → adresse, choisie par `REGISTRY_ROUTES_FILE`. Dans la pile du miroir, [routing.detenteurs.yaml](connectors/routing.detenteurs.yaml) : chaque détenteur est joint par la garde de la couche [consentement-minimisation](../consentement-minimisation/README.md) (hors Docker : `routing.detenteurs.local.yaml`). Registres en direct, sans garde : `routing.yaml` (tests de cette couche) et `routing.local.yaml`.
- **Par appel**, `query(…, client_id=…, consent_id=…)` : le demandeur de l'appel part dans `X-Road-Client` (par défaut celui du connecteur, `XROAD_CLIENT_ID`), la référence de l'accord du citoyen dans `X-Consent-Id`. Le corps reste celui du contrat des registres ; un registre ignore l'accord, la garde le vérifie. En mode X-Road, le demandeur doit être un sous-système déclaré (`INSTANCE/CLASSE/MEMBRE/SOUS-SYSTÈME`) : la couche démarches traduit chaque administration avec `XROAD_CLIENTS`.

## Spécifications et tests

- [openapi.yaml](openapi.yaml) : interface X-Road du Security Server du demandeur, telle que l'appelle le connecteur (`POST /r1/{instance}/{classe}/{membre}/{sous-système}/{service}`), avec la traduction des erreurs X-Road.
- [notifications.openapi.yaml](notifications.openapi.yaml) : service de notifications simulées, généré depuis `notifications/app.py`.
- [schemas/](schemas) : contrat des notifications (`notification-request.json`, `notification-response.json`, `sms-reply.json`) ; [examples/notification-exchanges.json](examples/notification-exchanges.json). Les échanges avec les registres suivent le contrat de la couche registres (`../registres/schemas`).
- Tests : `pip install -r requirements-dev.txt`, puis `python -m pytest` (74 tests). `requirements-dev.txt` installe aussi `../registres` : les tests d'interopérabilité font tourner les registres en mémoire derrière les connecteurs.

## À faire

- Outil « brancher un registre » pour l'épreuve en direct : déclarer le registre d'une autre équipe dans X-Road à partir de son adresse et de son fichier OpenAPI.
- Déclarer le registre ONI (`cnib-status`) dans le banc X-Road.
- Banc X-Road : faire pointer les services des fournisseurs (`setup_bench.py`, `PROVIDERS`) sur la garde (`http://consentement-minimisation:8000/holders/<détenteur>`) au lieu des registres. Sans cela, en mode X-Road, les appels contournent la garde (ni accord vérifié chez le détenteur, ni réduction, ni trace côté détenteur).
- Demandeurs X-Road : chaque appel part désormais avec l'administration du dossier (traduite par `XROAD_CLIENTS` ; la Fonction publique devient `BF/GOV/FONCTION-PUBLIQUE/RECRUTEMENT`, déclaré sur le banc). Reste à déclarer sur le banc un sous-système pour la DIPF (passeports) : sans lui, la démarche passeport est refusée en mode X-Road.
