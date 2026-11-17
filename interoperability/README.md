# Interopérabilité

Responsable : Personne 3.

```
interoperability/
├── registries/            registres simulés « officiels » : état civil, transports
│   └── common/            fabrique d'application, enveloppe, recherche de fiches
├── mock_registry/         autres registres fictifs : Justice, Police, Trésor
├── connectors/            connecteurs utilisés par le backend (direct, X-Road, notifications)
├── notifications/         service de notifications simulé (SMS, e-mail) et téléphone du citoyen
├── xroad/                 banc de test X-Road et sa configuration automatique
└── tests/
```

## Registres simulés

Chaque registre expose les mêmes routes :

| Route | Rôle |
|---|---|
| `POST /services/{service}` | Un service minimisé (requête et réponse selon `contracts/`) |
| `GET /services` | Liste des services |
| `GET /health` | État du registre |

`/services/{service}` est l'URL à déclarer comme service REST dans X-Road.

| Organisation (identifiant X-Road) | Port | Services | Réponse |
|---|---|---|---|
| `BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL` | 8101 | `identity` | Identité nécessaire à un titre, `born_in_burkina`, `deceased` |
| | | `identity-match` | `match` : oui/non entre l'identifiant pivot et ce que déclare l'usager |
| | | `is-adult` | `adult` : oui/non, jamais la date de naissance |
| `BF/GOV/TRANSPORT/PERMIS` | 8102 | `driving-licence` | `valid`, catégories et échéance seulement si le permis est valide |
| `BF/GOV/JUSTICE/REGISTRES` | 8103 | `nationality` | `burkinabe` : oui/non, sans le mode d'acquisition |
| | | `criminal-record` | `clean` : oui/non, sans le détail |
| `BF/GOV/POLICE/PERTES` | 8104 | `loss-declaration` | `declared`, référence du procès-verbal (`parameters.document_type`, CNIB par défaut) |
| `BF/GOV/TRESOR/PAIEMENTS` | 8105 | `payment-status` | `paid`, référence (exige `procedure`) |

Le Trésor a aussi deux routes de démonstration, hors contrat : `POST /simulate/payments` et `POST /simulate/payments/{reference}/pay`.

Variables : `REFERENCE_DATE` (figer « aujourd'hui »), `SIMULATED_LATENCY_MS` (latence ajoutée), `ORGANIZATION` (changer l'identifiant).

### Personnes de test et cas pièges

| Identifiant pivot | Personne | Cas |
|---|---|---|
| `ACTE:OUAGA:2004:01234` | Awa KABORE | Parcours nominal : née au Burkina, permis B, a payé sa CNIB |
| `ACTE:OUAGA:1979:00412` | Awa KABORE | Même nom, autre date de naissance : pas d'ambiguïté |
| `ACTE:OUAGA:1998:00456` | Issa SAWADOGO | Né à Abidjan : la Justice doit confirmer la nationalité ; paiement non reçu |
| `ACTE:OUAGA:2012:02210` | Fatimata OUEDRAOGO | Mineure |
| `ACTE:OUAGA:2008:03175` | Boukary ZONGO | Majeur le 2026-11-19 |
| `ACTE:OUAGA:2008:00560` | Sali BAMBARA | Née un 29 février |
| `ACTE:OUAGA:1995:00321` et `00322` | Moussa TRAORE ×2 | Homonymes nés le même jour au même endroit : `ambiguous` par critères |
| `ACTE:OUAGA:1961:00087` | Salif NIKIEMA | Décédé |
| `ACTE:OUAGA:1990:01502` | Aminata OUÉDRAOGO | Nom accentué : trouvée en cherchant « OUEDRAOGO » |
| `ACTE:OUAGA:1985:00789` | Kofi MENSAH | Nationalité acquise par naturalisation |
| `ACTE:OUAGA:1992:01120` | Adama SOME | Casier avec condamnation |
| `ACTE:OUAGA:2000:00654` | Rasmané ILBOUDO | Né à Lomé, absent du registre de la Justice : `not_found` |
| `ACTE:OUAGA:1997:00933` | Mariam OUATTARA | CNIB déclarée perdue |
| `ACTE:OUAGA:1988:00230` | Paul YAMEOGO | Passeport perdu (pas la CNIB) ; permis B et C |
| `ACTE:OUAGA:2003:09999` | — | Absent de l'état civil : `not_found` |

## Connecteurs (pour le backend)

Ils respectent le `Protocol` `RegistryConnector` du backend, sans l'importer :

```python
from connectors import build_connector

connector = build_connector()          # lit REGISTRY_CONNECTOR, etc.
reply = connector.query(
    "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
    "identity",
    {"procedure": "cnib-application", "subject": {"pivot_id": "ACTE:OUAGA:2004:01234"}},
)
reply["status"]   # "ok", "not_found", "ambiguous", "refused", "unavailable" ou "invalid_request"
```

| Variable | Rôle |
|---|---|
| `REGISTRY_CONNECTOR` | `direct` (défaut) ou `xroad` |
| `REGISTRY_ROUTES_FILE` | Connecteur direct : table organisation vers URL (défaut `connectors/routing.yaml`, noms Docker ; `routing.local.yaml` hors Docker) |
| `XROAD_SECURITY_SERVER_URL` | Connecteur X-Road : serveur de sécurité du demandeur (banc : `http://ss-demandeurs:8080`) |
| `XROAD_CLIENT_ID` | Identifiant X-Road du demandeur (défaut `BF/GOV/ONI/CNIB`) |
| `REGISTRY_TIMEOUT_S` | Délai d'attente (défaut 3 s) |

Garanties :

- `query()` ne lève jamais d'exception pour un problème de registre. Une panne, un délai dépassé ou une réponse illisible donnent `unavailable`.
- Une réponse `ok` sans données, ou avec un code HTTP d'erreur, n'est pas acceptée.
- Les données jointes à un statut autre que `ok` sont supprimées.
- Le `payload` de l'appelant n'est pas modifié ; un `request_id` est ajouté s'il manque.

Installation dans le backend : `pip install -e ../interoperability` (n'apporte que `httpx` et `PyYAML`).

Le connecteur X-Road est validé sur le banc X-Road 7.8.3 : voir [xroad/README.md](xroad/README.md).

## Notifications simulées

Passerelle SMS et e-mail fictive, port 8106. Rien n'est réellement envoyé : les messages arrivent dans une boîte d'envoi et sur un téléphone simulé, d'où le citoyen peut répondre. C'est l'étape 4 de la démo du guide (« un SMS part, le citoyen répond OUI, la requête repart »).

| Page | Usage |
|---|---|
| http://localhost:8106 | Boîte d'envoi : tous les messages envoyés et les réponses reçues |
| http://localhost:8106/phone/22670000001 | Téléphone simulé d'Awa : SMS reçus, boutons de réponse, saisie libre |

Le frontend peut afficher ce téléphone dans un `<iframe>` à côté de l'écran agent, ou construire son propre écran avec les routes ci-dessous.

### Côté backend

```python
from connectors import build_notifier

notifier = build_notifier()            # lit NOTIFICATION_SERVICE_URL
result = notifier.send_sms(
    "22670000001",
    "Dossier DOS-2026-0042 : la Fonction publique demande à vérifier 3 informations. "
    "Répondez 1 pour OUI, 2 pour NON.",
    notification_id="DOS-2026-0042:consentement:1",   # clé d'idempotence
    reference="DOS-2026-0042",
    reply_choices=["1", "2"],
)
result["status"]   # "sent", "failed", "invalid_request" ou "unavailable"
```

`send_email(recipient, subject, message, ...)` envoie un e-mail. Le backend reçoit les réponses du citoyen de deux façons, au choix :

- **par webhook** : si `NOTIFICATION_REPLY_WEBHOOK_URL` est défini, chaque réponse y est envoyée en `POST` dès sa réception ([sms-reply.json](../contracts/schemas/sms-reply.json)). La route du backend répond `2xx` et ignore un `reply_id` déjà vu ;
- **par lecture** : `notifier.replies(after=cursor)` renvoie les réponses arrivées depuis le dernier `cursor`. C'est aussi le rattrapage si le backend était éteint au moment de la réponse.

`reference` est recopiée dans la réponse : le backend retrouve le dossier. Le texte reste brut (`"1"`) : c'est le backend qui décide que 1 veut dire oui.

Garanties :

- Les méthodes du client ne lèvent jamais d'exception. Panne, délai dépassé ou réponse illisible donnent `unavailable` : relancer plus tard **avec le même `notification_id`**.
- Un `notification_id` déjà traité n'envoie rien une seconde fois (`duplicate: true`). Réutilisé pour un autre message : refusé (HTTP 409).
- Un message contenant un identifiant pivot est refusé : un SMS ne porte que la référence du dossier.
- Les journaux masquent le destinataire (`226*****001`) et ne contiennent jamais le texte.

### Routes

| Route | Rôle |
|---|---|
| `POST /notifications` | Envoyer ([notification-request](../contracts/schemas/notification-request.json) → [notification-response](../contracts/schemas/notification-response.json)) |
| `GET /replies?after=<seq>` | Réponses du citoyen, dans l'ordre d'arrivée, avec `cursor` |
| `GET /notifications` | Messages envoyés, du plus récent au plus ancien (filtres `recipient`, `reference`, `channel`) |
| `GET /notifications/{id}` | Un message, avec `answered` |
| `POST /simulate/replies` | Démo : le citoyen répond (`sender`, `text`, `in_reply_to` facultatif) |
| `GET /simulate/phones/{numéro}/thread` | Démo : fil du téléphone simulé |
| `POST /simulate/reset` | Démo : tout effacer |

Sans `in_reply_to`, une réponse est rattachée au dernier SMS à choix reçu par ce numéro.

Destinataires toujours injoignables, pour tester l'échec : `22670000099` et `injoignable@exemple.bf` (statut `failed`).

| Variable | Rôle |
|---|---|
| `NOTIFICATION_SERVICE_URL` | Client : adresse du service (défaut `http://notifications:8000` ; hors Docker `http://localhost:8106`) |
| `NOTIFICATION_TIMEOUT_S` | Client : délai d'attente (défaut 3 s) |
| `NOTIFICATION_REPLY_WEBHOOK_URL` | Service : route du backend qui reçoit les réponses (vide : pas de webhook) |
| `SIMULATED_LATENCY_MS` | Service : latence ajoutée à chaque envoi |

Limites : messages gardés en mémoire (perdus au redémarrage du conteneur, le backend garde sa propre trace) ; pas d'appel vocal ; webhook sans authentification, acceptable sur le réseau Docker interne seulement.

## Tests

```bash
cd interoperability
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Les tests vérifient chaque requête et chaque réponse par rapport aux schémas de `contracts/`.
