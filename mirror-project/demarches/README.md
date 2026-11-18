# Couche démarches (API métier)

Responsable : Personne 2.

Copie de `backend/` (le dossier d'origine reste sur `main`), qui installe les connecteurs depuis `../passerelle` au lieu de `../interoperability`.

La carte du jury ne nomme pas cette couche : c'est l'orchestration des démarches (catalogue, dossiers, vérifications). Les deux couches obligatoires qu'elle contenait en sont sorties : [consentement-minimisation](../consentement-minimisation/README.md) et [journal](../journal/README.md).

**Accords** : la couche démarches recueille la décision du citoyen (espace usager, code reçu par SMS au guichet), en vérifie la forme (questions de la démarche, durée) et la fait enregistrer par le registre des accords de la couche consentement-minimisation (`app/consents.py`, client `consent_client`), avec son périmètre exact : pour chaque question, le détenteur et le service. C'est ce registre qui inscrit l'accord et son retrait au journal. Avant chaque vérification, l'accord actif y est relu ; chaque appel part ensuite avec le demandeur (`X-Road-Client`, l'administration du dossier, traduite par `XROAD_CLIENTS` en mode X-Road) et la référence de l'accord (`X-Consent-Id`), que la garde du détenteur revérifie. Registre des accords injoignable : rien n'est enregistré ni vérifié (503). Les anciennes tables `consents` et `consent_questions` ne sont plus écrites ; elles restent pour les migrations.

**Journal** : chaque événement d'un dossier est inscrit dans la couche [journal](../journal/README.md) (`app/journal.py`, client `journal_client`), avant la validation de l'action. Si le journal ne répond pas, l'action est annulée (503) : aucune action sans trace. `GET /v1/cases/{id}/journal` et l'audit de l'administration locale (`GET /v1/admin/audit`) y lisent. L'ancienne table `audit_events` n'est plus écrite ; elle reste pour les migrations.

## Lancer et tester

- Service `demarches` de `mirror-project/compose.yaml` (port 8000), construit depuis `mirror-project/` ([Dockerfile](Dockerfile)).
- Variables du journal : `JOURNAL_URL` (`http://journal:8000` dans Docker), `JOURNAL_TOKEN` (jeton de service `demarches`).
- Variables des accords : `CONSENT_URL` (`http://consentement-minimisation:8000`), `CONSENT_TOKEN`, `XROAD_CLIENTS` (« administration=sous-système X-Road », facultatif) ; `REGISTRY_ROUTES_FILE` désigne dans Docker `passerelle/connectors/routing.detenteurs.yaml`, pour joindre chaque détenteur par la garde.
- Tests : `pip install -r requirements-dev.txt`, puis `python -m pytest` (43 tests ; le journal y est remplacé par `journal_client.MemoryJournal`, le registre des accords tourne en mémoire).

## Démarche lancée par le citoyen

`POST /v1/citizen/cases` (rôle citoyen, compte rattaché à un acte) : le citoyen choisit une démarche publiée et autorise ses vérifications dans le même geste ; l'administration qui propose la démarche est la demandeuse (ses droits d'échange s'appliquent), l'accord est enregistré au journal, puis les vérifications partent aussitôt. Les vérifications (`_run_checks`) sont communes avec le guichet (`POST /v1/cases/{id}/checks`). C'est ce qui rend une démarche complète possible sans la couche bonus du guichet.

## Signalement d'une consultation

`POST /v1/cases/{id}/journal/{consultation}/report` (rôle citoyen, seulement le citoyen du dossier), avec `reason` :

- `not_me` : « je ne reconnais pas cette consultation » (contestation), inscrit `consultation_contested` ;
- `wrong_result` : une information du registre est fausse, inscrit `correction_requested` (correction à demander à la source).

Seule une consultation d'un registre (`registry_check`) peut être signalée, une fois pour chaque sorte. Le signalement est un événement du journal rattaché à la consultation (`correlation_id`) : l'administration demandeuse le lit dans `GET /v1/cases/{id}/journal`, comme le citoyen. Aucun texte libre n'est conservé.

## Spécification

[openapi.yaml](openapi.yaml) : contrat de l'API du miroir, issu de `contracts/openapi/backend.yaml` (branche `main`) et complété avec les routes ajoutées dans le miroir (`POST /v1/citizen/cases`, signalement, preuve du rattachement). Il couvre toutes les routes de l'application (comparaison faite avec la liste des routes FastAPI) et passe `openapi-spec-validator`. Trois erreurs de l'original y sont corrigées : deux descriptions coupées par une virgule (lignes 71 et 291) et le schéma `Error`, référencé mais rangé parmi les réponses.

`schemas/citizen.json` et `schemas/request.json` : schémas réservés (vides), à définir.

## Démarrage sur une base neuve

`scripts/start.py` crée le schéma actuel puis marque la base à la dernière révision Alembic quand la base est vide (sinon `alembic upgrade head`). Sans cela, la migration 0001 (tables d'après les modèles actuels) puis 0005 à 0009 rajoutaient des colonnes déjà présentes. Correction reprise de `backend/`, à relire.
