# Couche consentement et minimisation

Couche obligatoire de la carte du jury. Extraite de la couche démarches le 18/11/2026. Responsable : à désigner (proposition : Personne 2).

## Rôle

- **Ne transmettre que l'utile** : « majeur : oui », jamais la date de naissance. Rien ne sort de chez le détenteur avant d'avoir été réduit à la réponse utile.
- **Appliquer les règles de consentement** : qui peut demander quoi, pour quelle démarche, avec quel accord du citoyen.
- **Fonctionner devant n'importe quel registre** qui respecte le contrat, y compris celui d'une autre équipe (épreuve en direct).

Enchaînement : registre → consentement et minimisation → journal → passerelle.

## Fonctionnement

Un service (port 8109), avec deux parties.

**Registre des accords** (`/v1/consents`, côté demandeur). La couche démarches recueille la décision du citoyen (espace usager, ou code reçu par SMS au guichet) et la fait enregistrer ici, avec son périmètre exact : pour chaque question, le détenteur et le service interrogés. Une nouvelle décision remplace l'accord en cours du dossier ; le citoyen peut retirer son accord ; il expire à la date prévue. Chaque décision et chaque retrait sont inscrits dans la couche [journal](../journal/README.md) avant d'être enregistrés : journal injoignable, rien n'est enregistré.

**Garde** (`/holders/{détenteur}/services/{service}`, côté détenteur). La passerelle joint chaque détenteur par elle ([routing.detenteurs.yaml](../passerelle/connectors/routing.detenteurs.yaml)), jamais en direct. Même contrat que les registres ([registres/schemas](../registres/schemas)), avec deux en-têtes : `X-Road-Client` (demandeur) et `X-Consent-Id` (accord). Pour chaque demande :

1. L'accord doit être actif et couvrir ce demandeur (ou l'un de ses sous-systèmes X-Road), cette démarche, cette personne (identifiant pivot) et ce service. Sinon : `refused`, avec le motif, et le registre n'est pas appelé.
2. La garde appelle le registre avec le corps reçu, sans l'accord.
3. Elle réduit la réponse selon la règle du service ([holders.yaml](consent_service/holders.yaml)). Une réponse qui ne s'y prête pas devient `unavailable`, jamais « oui ». Le texte libre du registre ne sort pas : la garde écrit ses propres messages.
4. Elle inscrit la réponse (`holder_response`) ou le refus (`holder_refusal`) au journal, avec ce qui est sorti (catégories, jamais les valeurs), l'accord et l'identifiant de la requête. Journal injoignable : aucune donnée ne sort.

Réductions déclarées dans `holders.yaml` :

| Règle | Ce qui sort | Exemple |
|---|---|---|
| `keep: {champ: boolean}` | ces champs seulement, de ce type | Trésor : `paid`, sans la référence ni le montant du paiement |
| `found: true` | « fiche retrouvée : oui » | État civil, `identity` : la fiche complète (noms, date et lieu de naissance) ne sort pas |
| `adult_from: champ` | « majeur : oui/non », calculé depuis une date de naissance | registre d'une autre équipe qui ne renvoie que la fiche |

Une base `citizen_request` ouvre un service sans accord enregistré, pour les seules démarches listées : c'est le cas d'`identity-match`, quand le citoyen prouve lui-même qu'il est titulaire de son acte (rattachement de son compte).

Dans le journal, chaque consultation apparaît des deux côtés, reliés par l'identifiant de la requête (`correlation_id`) : `registry_check` (couche démarches : question, résultat) et `holder_response` (cette couche : ce qui est sorti de chez le détenteur).

## Spécifications

- [openapi.yaml](openapi.yaml), généré depuis l'application ; [schemas/consent.json](schemas/consent.json), schéma d'un accord, généré depuis le modèle. Régénérer les deux : `python -m consent_service.openapi` (un test vérifie qu'ils sont à jour).

| Route | Accès | Rôle |
|---|---|---|
| `POST /v1/consents` | jeton de service | Enregistrer la décision du citoyen pour un dossier |
| `GET /v1/consents?case_id=…&subject_ref=…&active=…` | jeton de service | Accords d'un dossier ou d'un citoyen |
| `GET /v1/consents/{id}` | jeton de service | Lire un accord |
| `POST /v1/consents/{id}/revoke` | jeton de service | Retirer un accord actif |
| `POST /holders/{détenteur}/services/{service}` | passerelle | Interroger un détenteur au travers de la garde |
| `GET /holders` | libre | Détenteurs servis, et ce que chaque service laisse sortir |
| `GET /health` | libre | État du service |

## Lancer

Avec tout le miroir : `docker compose up -d --build` depuis `mirror-project/` ; service `consentement-minimisation`, port 8109.

Depuis la machine, pour voir les règles et un refus :

```bash
curl http://localhost:8109/holders
curl -X POST http://localhost:8109/holders/etat-civil/services/identity \
  -H "Content-Type: application/json" -H "X-Road-Client: BF/GOV/DIPF/PASSEPORTS" \
  -d '{"procedure":"passeport_ordinaire_precheck","subject":{"pivot_id":"ACTE:OUAGA:2004:01234"},"parameters":{}}'
# → refused : « Aucun accord du citoyen n'accompagne la demande », inscrit au journal (holder_refusal)
```

Variables : `DATABASE_URL` (base `consentement`, créée au démarrage si elle manque), `CONSENT_TOKENS` (« couche=jeton »), `JOURNAL_URL` et `JOURNAL_TOKEN`, `HOLDERS_FILE` (autre fichier de détenteurs), `REGISTRY_TIMEOUT_S`, `REFERENCE_DATE` (« aujourd'hui » figé, comme les registres).

## Brancher le registre d'une autre équipe

Avec l'outil de la passerelle, pile démarrée : `python3 passerelle/brancher.py remplacer etat-civil <adresse> --essai <pivot>` (mode d'emploi : [passerelle/README.md](../passerelle/README.md#brancher-le-registre-dune-autre-équipe)). Il écrit un fichier dans `infrastructure/branchements/` (`HOLDERS_OVERRIDES`), que la garde relit à chaque appel : sans redémarrage, elle interroge le registre de l'autre équipe avec nos règles. `GET /holders` montre l'adresse et l'origine (`base` ou fichier) de chaque détenteur ; un fichier invalide est ignoré et signalé par `GET /health` (`branchement_error`).

Pour un nouveau détenteur (`ajouter`), il reste à créer ses questions et leur droit d'échange dans la couche démarches (console d'administration locale).

Le corps envoyé à son registre est celui du contrat des registres, sans l'accord. Le contrat du jury, une fois publié, peut demander une autre forme d'appel : un adaptateur de plus dans la garde.

## Client pour la couche démarches

`consent_client` (installé par `pip install -e ../consentement-minimisation`, dépend seulement d'`httpx`) : `ConsentClient` (`record`, `revoke`, `get`, `search`, `active`), `consents_from_env()` (`CONSENT_URL`, `CONSENT_TOKEN`, `CONSENT_TIMEOUT_S`). `ConsentRefused` : demande refusée (404, 409, 422) ; `ConsentServiceUnavailable` : couche ou journal injoignable.

## Tests

`pip install -r requirements-dev.txt -e .`, puis `python -m pytest` : 62 tests, dont :

- registre des accords : décision, remplacement, retrait, expiration, journal, jetons ;
- garde devant les six registres simulés, en mémoire : seule la réponse utile sort (fiche complète réduite à « retrouvée », paiement sans référence ni montant, majorité calculée sans transmettre la date) ;
- onze cas de refus, sans appel au registre ;
- registre en panne ou réponse non conforme : jamais « oui » ; journal injoignable : aucune donnée ;
- bout en bout connecteur de la passerelle → garde → registre ; spécifications à jour ;
- branchements : registre remplacé sans redémarrage, détenteur ajouté, fichier invalide ignoré.

## Limites

- Une seule instance sert les six détenteurs simulés ; dans l'architecture cible, chaque détenteur exploite sa garde.
- Mode direct : l'en-tête `X-Road-Client` est déclaratif. Avec X-Road, il est authentifié par les serveurs de sécurité ; le banc publie désormais ses services à l'adresse de la garde, mais n'a pas été relancé pour le vérifier (5,3 Go de mémoire).
- Jetons de service statiques, pour la démonstration.
- Les accords enregistrés avant le 18/11 dans l'ancienne table `consents` de la couche démarches ne sont pas repris : les dossiers de démonstration plus anciens n'ont plus d'accord actif.
