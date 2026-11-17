# Interopérabilité

Responsable : Personne 3.

```
interoperability/
├── registries/            registres simulés « officiels » : état civil, transports
│   └── common/            fabrique d'application, enveloppe, recherche de fiches
├── mock_registry/         autres registres fictifs : Justice, Police, Trésor
├── connectors/            connecteurs utilisés par le backend (direct, X-Road)
├── xroad/                 configuration X-Road (phase 3)
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
| | | `criminal-record-current` | `valid` : oui/non, bulletin en cours de validité, sans condamnations |
| `BF/GOV/ONI/CNIB` | 8106 | `cnib-status` | `valid` : oui/non, sans numéro ni dates de validité |
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
| `XROAD_SECURITY_SERVER_URL` | Connecteur X-Road : serveur de sécurité du demandeur |
| `XROAD_CLIENT_ID` | Identifiant X-Road du demandeur (défaut `BF/GOV/ONI/CNIB`) |
| `REGISTRY_TIMEOUT_S` | Délai d'attente (défaut 3 s) |

Garanties :

- `query()` ne lève jamais d'exception pour un problème de registre. Une panne, un délai dépassé ou une réponse illisible donnent `unavailable`.
- Une réponse `ok` sans données, ou avec un code HTTP d'erreur, n'est pas acceptée.
- Les données jointes à un statut autre que `ok` sont supprimées.
- Le `payload` de l'appelant n'est pas modifié ; un `request_id` est ajouté s'il manque.

Installation dans le backend : `pip install -e ../interoperability` (n'apporte que `httpx` et `PyYAML`).

Le connecteur X-Road n'a été testé qu'avec des réponses simulées : il sera validé sur le banc X-Road en phase 3.

## Tests

```bash
cd interoperability
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Les tests vérifient chaque requête et chaque réponse par rapport aux schémas de `contracts/`.
