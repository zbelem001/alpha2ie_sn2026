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

## Spécifications et tests

- [openapi.yaml](openapi.yaml) : interface X-Road du Security Server du demandeur, telle que l'appelle le connecteur (`POST /r1/{instance}/{classe}/{membre}/{sous-système}/{service}`), avec la traduction des erreurs X-Road.
- [notifications.openapi.yaml](notifications.openapi.yaml) : service de notifications simulées, généré depuis `notifications/app.py`.
- Tests : `pip install -r requirements-dev.txt`, puis `python -m pytest` (74 tests). `requirements-dev.txt` installe aussi `../registres` : les tests d'interopérabilité font tourner les registres en mémoire derrière les connecteurs.

## À faire

- Outil « brancher un registre » pour l'épreuve en direct : déclarer le registre d'une autre équipe dans X-Road à partir de son adresse et de son fichier OpenAPI.
- Déclarer le registre ONI (`cnib-status`) dans le banc X-Road.
- Un demandeur X-Road par démarche : aujourd'hui, la couche démarches utilise un seul `XROAD_CLIENT_ID` ; en mode X-Road, la démarche passeport serait refusée (pas de droit sur le casier pour `ONI/CNIB`).
