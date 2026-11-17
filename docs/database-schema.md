# Modèle de données du backend — MVP

## Périmètre

PostgreSQL est déjà préparé par le lot infrastructure : `infrastructure/postgres/init/01-create-databases.sh` crée une base `backend` et une base `keycloak`. Le backend utilise uniquement la base `backend`. La personne 2 définit et implémente son schéma, ses migrations et son accès depuis FastAPI ; la personne 3 fournit le service PostgreSQL dans Compose.

Ce modèle couvre les scénarios de démonstration `concours_direct_preverification` et `passeport_ordinaire_precheck` : des pré-vérifications limitées, un consentement lié aux questions, des requêtes ciblées vers les registres simulés, les tentatives et le journal consultable par le citoyen. Les données des registres de démonstration sont fictives et produites par l’équipe.

## Principes

- Le backend conserve des **références** à la personne, au dossier et aux démarches, pas de fiche citoyen centrale.
- Ne jamais enregistrer les données brutes des registres (date de naissance, acte, casier, etc.) ni les corps complets de réponses. Seuls le statut et le résultat minimal utile au dossier peuvent être conservés si la règle le prévoit.
- Le consentement est accordé par le citoyen avant les consultations ; sa portée couvre un dossier et les questions de ce dossier. Un refus ou une révocation bloque les appels qui n’ont pas encore été envoyés.
- Une requête métier est stable et idempotente ; chaque exécution/réessai est une tentative distincte.
- Le journal est append-only dans l’application : correction par nouvel événement, pas de modification/suppression d’une entrée existante. Le hash chaîné est une protection contre les modifications accidentelles, pas une preuve cryptographique indépendante sans ancrage externe.
- Les durées de conservation et la suppression/archivage doivent être configurés et validés par l’équipe ; aucune durée arbitraire n’est codée dans le schéma.

## Entités et relations

```mermaid
erDiagram
    ADMINISTRATION ||--o{ REGISTRY : exposes
    REGISTRY ||--o{ QUESTION : provides
    ADMINISTRATION ||--o{ PERMISSION : requests
    QUESTION ||--o{ PERMISSION : allows
    ADMINISTRATION ||--o{ PROCEDURE : owns
    PROCEDURE ||--o{ PROCEDURE_QUESTION : requires
    QUESTION ||--o{ PROCEDURE_QUESTION : answers
    PROCEDURE ||--o{ CASE : instantiates
    ADMINISTRATION ||--o{ CASE : requests
    CASE ||--o{ CONSENT : authorizes
    CONSENT ||--o{ CONSENT_QUESTION : covers
    QUESTION ||--o{ CONSENT_QUESTION : included
    CASE ||--o{ REGISTRY_REQUEST : contains
    QUESTION ||--o{ REGISTRY_REQUEST : checks
    REGISTRY_REQUEST ||--o{ REQUEST_ATTEMPT : retries
    CASE ||--o{ AUDIT_EVENT : records
```

### Tables MVP

| Table | Rôle et champs essentiels |
|---|---|
| `administrations` | Demandeurs/fournisseurs : `id`, `code` unique, `name`, `active`. |
| `registries` | Registres connectés : `id`, `administration_id`, `code`, `connector_config_ref`, `active`. Pas de secrets de connexion en clair ; garder les URL/configuration technique dans l’environnement ou un secret store. |
| `questions` | Catalogue de réponses autorisées : `id`, `code` unique, `registry_id`, `service_code`, `response_key`, `description`, `active`. Pour le concours, `criminal-record` → `clean` reste un indicateur à revoir humainement. Pour le passeport adulte, ONI répond à `cnib-status` par `valid` et Justice expose `nationality` et `criminal-record-current` → `valid`, sans numéro CNIB ni contenu du bulletin. |
| `permissions` | Autorisations d’appel : `requester_administration_id`, `question_id`, `active`, dates de validité. Contrainte unique sur demandeur + question. |
| `procedures` | Catalogue des démarches : `id`, `code` unique, `owner_administration_id`, `title`, `active`, `config_version`. |
| `procedure_questions` | Questions requises par démarche et ordre : `procedure_id`, `question_id`, `required`, `position`. Contrainte unique sur démarche + question. |
| `cases` | Dossier d’une démarche : `id`, `procedure_id`, `requester_administration_id`, `subject_ref`, `status`, `created_at`, `updated_at`, `closed_at`. `subject_ref` est l’identifiant fictif/pivot fourni par le système d’identité ; pas de nom, date de naissance ou adresse. |
| `consents` | Consentement : `id`, `case_id`, `subject_ref`, `status` (`granted`, `refused`, `revoked`, `expired`), `granted_at`, `revoked_at`, `expires_at`, `notice_version`, `channel`, `evidence_ref`. L’agent ne peut pas donner le consentement à la place du citoyen. |
| `consent_questions` | Portée du consentement : `consent_id`, `question_id`. Cela garantit le consentement limité aux questions de la démarche. |
| `registry_requests` | Vérification logique : `id`, `case_id`, `question_id`, `status`, `idempotency_key` unique, `attempt_count`, `minimal_result` JSONB nullable, `created_at`, `updated_at`. `minimal_result` ne contient que la réponse métier nécessaire, jamais la réponse brute. |
| `request_attempts` | Tentative d’appel/réessai : `id`, `registry_request_id`, `attempt_number`, `status`, `started_at`, `finished_at`, `transport_id`, `error_code`. Contrainte unique sur requête + numéro de tentative. Aucun body brut de requête/réponse. |
| `audit_events` | Journal métier append-only : `id`, `case_id`, `subject_ref`, `actor_type`, `actor_ref`, `requester_administration_id`, `registry_id`, `question_id`, `event_type`, `outcome`, `purpose`, `data_categories` JSONB, `occurred_at`, `correlation_id`, `previous_hash`, `event_hash`. Aucune valeur de registre. |

Les notifications simulées peuvent être ajoutées après le flux principal ; elles ne sont pas requises pour stocker le consentement, les demandes et l’historique du MVP.

## États du MVP

- Dossier : `received`, `in_progress`, `pending`, `completed`, `rejected`, `cancelled`.
- Requête/vérification : `queued`, `pending`, `confirmed`, `rejected`, `ambiguous`, `not_found`, `unavailable`, `blocked`, `error`.
- Tentative : `started`, `succeeded`, `failed`.
- Consentement : `granted`, `refused`, `revoked`, `expired`.

`unavailable` est récupérable et garde le dossier `pending`. Une nouvelle tentative réutilise la même `registry_request` et crée un nouveau `request_attempt`. Le statut global du dossier est calculé à partir des vérifications requises ; une vérification facultative ne doit pas empêcher la clôture.

## Ordre transactionnel d’une vérification

1. Charger le dossier, la démarche et les questions requises.
2. Vérifier l’autorisation demandeur/question et le consentement actif couvrant cette question.
3. Créer/récupérer la `registry_request` grâce à sa clé d’idempotence, puis créer un événement de journal pour l’appel autorisé (ou son blocage).
4. Appeler le connecteur hors transaction DB longue.
5. Enregistrer le statut minimal et une ligne `request_attempts` ; effacer de la mémoire applicative la réponse brute après extraction du résultat permis.
6. Ajouter un événement de journal pour le résultat, recalculer l’état du dossier et committer.

Chaque appel réel et chaque refus métier doit être visible dans `audit_events`. Ne pas journaliser les secrets, les attributs personnels bruts ni le payload complet.

## Contraintes et index à prévoir

- UUID pour les identifiants internes ; dates en `TIMESTAMPTZ` UTC.
- `UNIQUE(administrations.code)`, `UNIQUE(registries.administration_id, registries.code)`, `UNIQUE(questions.code)`, `UNIQUE(procedures.code)`.
- `UNIQUE(permissions.requester_administration_id, permissions.question_id)`.
- `UNIQUE(procedure_questions.procedure_id, procedure_questions.question_id)`.
- `UNIQUE(registry_requests.idempotency_key)` et `UNIQUE(request_attempts.registry_request_id, request_attempts.attempt_number)`.
- Index sur `cases(subject_ref, created_at)`, `cases(status, updated_at)`, `registry_requests(status, updated_at)` et `audit_events(subject_ref, occurred_at)`.
- Clés étrangères avec `RESTRICT` pour les entités de configuration utilisées et `CASCADE` uniquement pour les tables d’association de portée (ex. `consent_questions`). Ne pas supprimer en cascade un dossier ou un événement d’audit.

## Hors du premier schéma

Pas de table `citizens` contenant les attributs d’état civil, pas de copie des registres, pas de stockage d’image CNIB, d’acte ou de casier, et pas de notifications SMS réelles. La gestion d’identité et des sessions relève de Keycloak ; le backend ne garde qu’une référence d’acteur/administration utile à l’autorisation et à l’audit.

## Mise en route locale

Depuis `backend/`, après avoir démarré PostgreSQL avec `docker compose up -d postgres` à la racine :

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend .venv/bin/python -m scripts.seed_demo
DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend REGISTRY_ROUTES_FILE=../interoperability/connectors/routing.local.yaml .venv/bin/uvicorn app.main:app --reload
```

L’URL locale vise le port publié par Compose. Dans un futur conteneur backend, utiliser le nom de service `postgres` et le port interne `5432`. L’API expose actuellement `GET /health`; les dépôts et endpoints métier seront branchés ensuite sur `SessionLocal` / `get_db`.
