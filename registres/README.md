# Couche registres

Responsable : Personne 3. Couche obligatoire de la carte du jury.

Copie de `interoperability/registries` et `interoperability/mock_registry` (branche `mirror-project`). Les dossiers d'origine restent en place.

## Contenu

| Registre | Identifiant | Port | Services |
|---|---|---|---|
| État civil (`registries/civil_registry`) | `BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL` | 8101 | `identity`, `identity-match`, `is-adult` |
| Permis (`registries/transport_registry`) | `BF/GOV/TRANSPORT/PERMIS` | 8102 | `driving-licence` |
| Justice (`mock_registry/justice`) | `BF/GOV/JUSTICE/REGISTRES` | 8103 | `nationality`, `criminal-record` |
| Police (`mock_registry/police`) | `BF/GOV/POLICE/PERTES` | 8104 | `loss-declaration` |
| Trésor (`mock_registry/treasury`) | `BF/GOV/TRESOR/PAIEMENTS` | 8105 | `payment-status` |
| ONI (`mock_registry/oni`) | `BF/GOV/ONI/CNIB` | 8106 | `cnib-status` |

Une seule image ([Dockerfile](Dockerfile)) pour les six registres ; le registre lancé est choisi par la commande dans `infrastructure/docker-compose.couches.yml`.

## Spécification et tests

- [openapi.yaml](openapi.yaml) : contrat commun (`POST /services/{service}`, `GET /services`, `GET /health`), généré depuis `registries/common/app_factory.py`. **À remplacer par le contrat OpenAPI du jury dès sa publication.**
- Tests : `pip install -r requirements-dev.txt`, puis `python -m pytest` (36 tests). Aucune dépendance vers les autres couches.

## À faire

- Réécrire les registres selon le contrat du jury, sans rien y ajouter.
- Aujourd'hui, les registres réduisent eux-mêmes leur réponse (`is-adult` répond oui ou non). Dans l'architecture cible, cette réduction relève de la couche [consentement-minimisation](../consentement-minimisation/README.md), placée devant n'importe quel registre conforme au contrat.
