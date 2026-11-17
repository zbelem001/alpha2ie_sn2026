# Couche démarches (API métier)

Responsable : Personne 2.

Copie de `backend/` (branche `mirror-project`), qui installe les connecteurs depuis `../passerelle` au lieu de `../interoperability`. Le dossier d'origine reste en place.

La carte du jury ne nomme pas cette couche : c'est l'orchestration des démarches (catalogue, dossiers, vérifications). Elle contient aussi, pour l'instant, le code de deux couches obligatoires à extraire : [consentement-minimisation](../consentement-minimisation/README.md) et [journal](../journal/README.md).

## Lancer et tester

- Service `demarches` de `mirror-project/compose.yaml` (port 8000), construit depuis `mirror-project/` ([Dockerfile](Dockerfile)).
- Tests : `pip install -r requirements-dev.txt`, puis `python -m pytest` (28 tests).

## Spécification

[openapi.yaml](openapi.yaml) est une copie conforme de `contracts/openapi/backend.yaml` (racine du dépôt). Elle n'est pas valide en l'état (à corriger dans l'original) :

- lignes 71 et 291 : une virgule dans une description non entre guillemets coupe la valeur en deux clés YAML ;
- `#/components/schemas/Error` est référencé mais n'est pas défini.

`schemas/citizen.json` et `schemas/request.json` : schémas réservés (vides), à définir.

## Démarrage sur une base neuve

`scripts/start.py` crée le schéma actuel puis marque la base à la dernière révision Alembic quand la base est vide (sinon `alembic upgrade head`). Sans cela, la migration 0001 (tables d'après les modèles actuels) puis 0005 à 0009 rajoutaient des colonnes déjà présentes. Correction reprise de `backend/`, à relire.
