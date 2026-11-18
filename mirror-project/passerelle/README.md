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
- Tests : `pip install -r requirements-dev.txt`, puis `python -m pytest` (87 tests, dont l'outil « brancher un registre » et la cohérence du banc X-Road). `requirements-dev.txt` installe aussi `../registres` : les tests d'interopérabilité font tourner les registres en mémoire derrière les connecteurs.

## Brancher le registre d'une autre équipe

Épreuve en direct. Pile démarrée, depuis `mirror-project/`, sans reconstruire ni redémarrer : [brancher.py](brancher.py) (bibliothèque standard seulement).

```bash
python3 passerelle/brancher.py liste                      # détenteurs servis par la garde, et leur origine
python3 passerelle/brancher.py sonder http://192.168.1.42:8000 --regle is-adult=keep:adult --essai ACTE:OUAGA:2004:01234
python3 passerelle/brancher.py remplacer etat-civil http://192.168.1.42:8000 --essai ACTE:OUAGA:2004:01234
python3 passerelle/brancher.py retirer etat-civil
```

- **remplacer** : la garde interroge le registre de l'autre équipe à la place du nôtre, avec les mêmes règles ; nos démarches l'utilisent dès la demande suivante. C'est le cas d'un registre qui respecte le même contrat.
- **ajouter** : un nouveau détenteur, avec ses règles et sa route (`--organisation`, `--nom`, `--regle service=keep:champ`, `found` ou `adult_from:champ[@service]`). Il reste à créer ses questions dans la couche démarches (console d'administration locale).
- Avant d'écrire, l'outil sonde le registre : santé, services (`GET /services` ou `--openapi fichier`), et avec `--essai`, un appel par service pour vérifier que la règle de minimisation s'applique (seuls les noms des champs sont affichés). Si un service manque ou si une règle ne s'applique pas, rien n'est écrit (sauf `--force`).
- Le branchement est un fichier de `infrastructure/branchements/`, monté dans la garde et dans la couche démarches, relu à chaque appel. `--sonde URL` : adresse à sonder depuis la machine, si la garde joint le registre autrement.

Répété le 18/11 sur la pile : second registre d'état civil lancé à part (« équipe B »), sondé (règles applicables), branché ; la démarche d'Awa l'a interrogé à la place du nôtre ; débranché, retour à notre registre.

## À faire

- Outiller le branchement d'un registre étranger en mode X-Road (le déclarer comme fournisseur sur le banc) : aujourd'hui à la main, dans `PROVIDERS` de `xroad/configuration/setup_bench.py`.
