# Couche journal de traçabilité

Couche obligatoire de la carte du jury. Extraite de la couche démarches le 18/11/2026. Responsable : à désigner (proposition : Personne 2).

## Rôle

- Retrouver **chaque consultation** : qui a demandé quoi, quand, pour quelle démarche, sur quelle base.
- Recherche par citoyen, par demande et par date.
- Les refus et les pannes y figurent aussi, pas seulement les réponses positives.
- La vidéo imposée se termine sur l'usager qui retrouve la consultation dans son espace : l'espace usager lit ce journal par la couche démarches (`GET /v1/cases/{id}/journal`).

## Fonctionnement

- **Service à part**, avec sa propre base PostgreSQL (`journal`), créée au démarrage si elle manque.
- **Ajout seul** : aucune route ne modifie ni ne supprime un événement, et dans PostgreSQL un déclencheur refuse `UPDATE`, `DELETE` et `TRUNCATE`, même au service.
- **Chaîne d'empreintes** : chaque événement a un numéro d'ordre sans trou et une empreinte SHA-256 qui couvre tous ses champs et l'empreinte du précédent. `GET /v1/chain/verify` recalcule toute la chaîne et indique le premier événement modifié, retiré ou intercalé.
- **Source certifiée par le jeton** : la couche qui écrit est déduite de son jeton de service, une couche ne peut pas écrire au nom d'une autre.
- **Aucune valeur issue d'un registre** : des références (citoyen, dossier, accord, requête), des codes (démarche, question, administrations) et le résultat. Un champ hors contrat, comme une date de naissance, est refusé.
- **Pas d'action sans trace** : la couche démarches inscrit l'événement avant de valider l'action. Si le journal ne répond pas, l'action est annulée (503).

| Couche qui écrit | Événements |
|---|---|
| démarches | `case_created`, `consent_requested`, `consent_otp_simulated`, `consent_otp_sent`, `consent_otp_rejected`, `checks_blocked`, `check_blocked`, `registry_check` (une par consultation, avec l'identifiant de la requête en `correlation_id` et l'accord), `consultation_contested`, `correction_requested` |
| consentement-minimisation | `consent_recorded` et `consent_revoked` (registre des accords) ; `holder_response` (ce qui est sorti de chez le détenteur : catégories, jamais les valeurs) et `holder_refusal` (refus de la garde, avec le motif), reliés à la consultation par l'identifiant de la requête |

## Spécification et API

[openapi.yaml](openapi.yaml), généré depuis l'application (`python -m journal_service.openapi > openapi.yaml` ; un test vérifie qu'il est à jour).

| Route | Jeton | Rôle |
|---|---|---|
| `POST /v1/events` | écriture | Inscrire un événement |
| `GET /v1/events` | lecture | Rechercher : `subject_ref` (citoyen), `case_id` (demande), `correlation_id` (consultation), `from` et `to` (dates), `event_type` (répétable), `requester_code`, `actor_type`, `q` (texte), `order`, pages par `after` et `limit` |
| `GET /v1/events/{id}` | lecture | Lire un événement |
| `GET /v1/chain/verify` | lecture | Vérifier la chaîne d'empreintes |
| `GET /health` | aucun | État du service |

## Lancer

Avec tout le miroir : `docker compose up -d --build` depuis `mirror-project/` ; service `journal`, port 8108. Jetons de démonstration dans `.env.example` : `demarches` (écriture et lecture), `consentement-minimisation` (écriture), `auditeur` (lecture).

Épreuve « retrouver chaque consultation dans le journal », depuis la machine :

```bash
J="Authorization: Bearer dev-journal-auditeur"
curl -H "$J" "http://localhost:8108/v1/events?subject_ref=ACTE:OUAGA:2004:01234&event_type=registry_check"
curl -H "$J" "http://localhost:8108/v1/events?case_id=<identifiant du dossier>"
curl -H "$J" "http://localhost:8108/v1/events?subject_ref=ACTE:OUAGA:2004:01234&from=2026-11-18T00:00:00Z&to=2026-11-19T00:00:00Z"
curl -H "$J" "http://localhost:8108/v1/chain/verify"
```

Variables : `DATABASE_URL`, `JOURNAL_WRITE_TOKENS` et `JOURNAL_READ_TOKENS` (« couche=jeton », séparés par des virgules, 16 caractères au moins). Sans jeton configuré, tout appel est refusé.

## Client pour les autres couches

`journal_client`, installé par `pip install -e ../journal` (dépend seulement d'`httpx`) :

- `JournalClient` : `append`, `get`, `search` (pages enchaînées). `append` lève `JournalUnavailable` si l'événement n'est pas inscrit ;
- `journal_from_env()` : `JOURNAL_URL`, `JOURNAL_TOKEN`, `JOURNAL_TIMEOUT_S` (3 s par défaut) ;
- `MemoryJournal` : même interface en mémoire, pour les tests des couches qui écrivent au journal (un test vérifie qu'il se comporte comme le service).

## Tests

`pip install -r requirements-dev.txt -e .`, puis `python -m pytest` : 33 tests (inscription, jetons, ajout seul, détection d'une altération de la chaîne, recherche par citoyen, demande et date, pages, client et journal en mémoire, spécification à jour). Deux tests de plus contre un vrai PostgreSQL (déclencheur d'ajout seul, ajouts simultanés sans trou) si `JOURNAL_TEST_DATABASE_URL` désigne une base jetable (voir `tests/test_postgres.py`).

## Limites

- Jetons de service statiques, pour la démonstration. En production : authentification mutuelle d'X-Road ou identifiants clients OAuth.
- Un seul journal pour la démonstration. Dans l'architecture cible ([docs/architecture-socle.md](../docs/architecture-socle.md)), chaque détenteur tient le sien, et le portail les agrège pour l'usager.
- Le résultat de chaque vérification (`confirmed`, `rejected`) reste dans l'événement `registry_check`, comme avant, pour que l'usager le retrouve. Le document de référence (§5.6) ne prévoit que le statut de l'échange.
- Les événements inscrits avant le 18/11 dans l'ancienne table `audit_events` de la couche démarches ne sont pas repris.
- Pas encore d'horodatage externe de la dernière empreinte.
