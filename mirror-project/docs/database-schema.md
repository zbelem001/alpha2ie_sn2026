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
    REGISTRY ||--o{ REGISTRY_SERVICE : offers
    PROCEDURE ||--o{ CASE : instantiates
    ADMINISTRATION ||--o{ CASE : requests
    CASE ||--o{ CONSENT : authorizes
    CONSENT ||--o{ CONSENT_QUESTION : covers
    QUESTION ||--o{ CONSENT_QUESTION : included
    CASE ||--o{ REGISTRY_REQUEST : contains
    QUESTION ||--o{ REGISTRY_REQUEST : checks
    REGISTRY_REQUEST ||--o{ REQUEST_ATTEMPT : retries
    CASE ||--o{ AUDIT_EVENT : records
    ADMINISTRATION ||--o{ ADMINISTRATION_AUDIT_EVENT : manages
    CASE ||--o{ NOTIFICATION : alerts
    KEYCLOAK_ACCOUNT ||--o| CITIZEN_IDENTITY_LINK : maps
```

### Tables MVP

| Table | Rôle et champs essentiels |
|---|---|
| `administrations` | Demandeurs/fournisseurs : `id`, `code` unique, `name`, `active`. |
| `registries` | Registres : `id`, `administration_id`, `code`, `name`, `base_url`, `connector_config_ref`, `active`, dernier résultat du test simulé. Aucun secret de connexion n’est stocké ici. |
| `registry_services` | Services booléens déclarés par un registre : `registry_id`, `code`, `title`, `description`, `active`. Déclarer un service ne crée pas son connecteur. |
| `questions` | Catalogue de réponses autorisées : `id`, `code` unique, `registry_id`, `service_code`, `response_key`, `description`, `active`. Pour le concours, `criminal-record` → `clean` reste un indicateur à revoir humainement. Pour le passeport adulte, ONI répond à `cnib-status` par `valid` et Justice expose `nationality` et `criminal-record-current` → `valid`, sans numéro CNIB ni contenu du bulletin. |
| `permissions` | Autorisations d’appel : `requester_administration_id`, `question_id`, `status` (`not_requested`, `requested`, `approved`, `suspended`), `purpose`, `active`, dates de validité. Une demande reste inactive tant que la gouvernance n’a pas approuvé la convention. |
| `procedures` | Catalogue des démarches : `id`, `code` unique, `owner_administration_id`, `title`, `purpose`, `consent_days`, `published`, `active`, `config_version`. Une démarche déjà utilisée par un dossier ne peut pas être éditée en place. |
| `procedure_questions` | Questions requises par démarche et ordre : `procedure_id`, `question_id`, `required`, `position`, configuration d’affichage du document. Contrainte unique sur démarche + question. |
| `administration_audit_events` | Historique des actions de la console : administration, acteur Keycloak, action, cible, détail expurgé des PIN et secrets, date UTC. |
| `cases` | Dossier d’une démarche : `id`, `procedure_id`, `requester_administration_id`, `subject_ref`, `applicant_name` (nom d’affichage facultatif saisi par l’agent), `status`, `consent_channel` (`web` ou `assisted`), dates. `subject_ref` est la référence pivot fictive fournie par le système d’identité et partagée avec les registres du prototype ; elle est indexée, mais pas unique, car un citoyen peut avoir plusieurs dossiers. Ce n’est pas un identifiant officiel. Le nom n’est utilisé que pour l’affichage du dossier, sans date de naissance ni adresse. |
| `consents` | Consentement : `id`, `case_id`, `subject_ref`, `status` (`granted`, `refused`, `revoked`, `expired`), `granted_at`, `revoked_at`, `expires_at`, `notice_version`, `channel`, `evidence_ref`. L’agent ne peut pas donner le consentement à la place du citoyen. |
| `consent_questions` | Portée du consentement : `consent_id`, `question_id`. Cela garantit le consentement limité aux questions de la démarche. |
| `consent_otp_challenges` | Défi temporaire du recueil assisté : `case_id`, `requested_by_sub`, `provider_pin_id` nullable, empreinte HMAC pour le mode simulé, empreinte du périmètre, nombre d’essais, état (`sent` ou `simulated`), expiration et date de consommation. En mode fournisseur, le PIN est généré/vérifié par le fournisseur ; en simulation, aucun PIN brut n’est conservé. |
| `registration_otp_challenges` | Défi OTP avant inscription : `phone_number`, `provider_pin_id` nullable, empreinte HMAC en mode simulé, nombre d’essais, expiration et date de vérification. `phone_verified` reste faux après une validation simulée. La création du compte Keycloak reste séparée. |
| `registry_requests` | Vérification logique : `id`, `case_id`, `question_id`, `status`, `idempotency_key` unique, `attempt_count`, `minimal_result` JSONB nullable, `lookup_identifier_type`, `lookup_identifier_ciphertext`, `created_at`, `updated_at`. L’identifiant de document est chiffré et uniquement présent pour l’appel autorisé ; jamais dans le journal ni le résultat métier. |
| `request_attempts` | Tentative d’appel/réessai : `id`, `registry_request_id`, `attempt_number`, `status`, `started_at`, `finished_at`, `transport_id`, `error_code`. Contrainte unique sur requête + numéro de tentative. Aucun body brut de requête/réponse. |
| `audit_events` | Journal métier append-only : `id`, `case_id`, `subject_ref`, `actor_type`, `actor_ref`, `requester_administration_id`, `registry_id`, `question_id`, `event_type`, `outcome`, `purpose`, `data_categories` JSONB, `occurred_at`, `correlation_id`, `previous_hash`, `event_hash`. Aucune valeur de registre. |
| `notifications` | Alertes liées à un dossier : `recipient_ref`, canal (`platform` ou `sms`), texte de l’alerte, état de livraison, identifiant de message renvoyé par le fournisseur SMS et code d’erreur non sensible. L’adresse téléphonique n’est pas copiée dans la notification ; en mode d’essai, le fournisseur redirige tous les SMS vers `TEST_PHONE_NUMBER`. Le mode par défaut reste simulé. Les OTP de consentement sont suivis séparément dans `consent_otp_challenges`. |
| `citizen_identity_links` | Rattachement du compte Keycloak à une référence interne : `principal_sub` unique, `subject_ref` unique (`CITIZEN:<UUID>` en création libre, ou une ancienne référence `ACTE:...`), `phone_number`, `linked_at`. Le numéro sert au routage SMS et n’est pas copié dans les dossiers, journaux ou notifications. |
| `citizen_document_identifiers` | Références de documents déclarées par le citoyen : `principal_sub`, `subject_ref`, `identifier_type`, `registry_code`, `identifier_ciphertext`, `identifier_digest`, `created_at`. Les valeurs sont chiffrées par Fernet ; l’empreinte HMAC permet la recherche sans indexer la valeur en clair. Les types du prototype sont CNIB, acte de naissance, casier, nationalité, paiement et déclaration de perte. |

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
- `UNIQUE(citizen_identity_links.principal_sub)` et `UNIQUE(citizen_identity_links.subject_ref)` : un compte et une référence ne peuvent être liés qu’une seule fois.
- `UNIQUE(citizen_document_identifiers.principal_sub, identifier_type)` et `UNIQUE(identifier_digest)` : un seul identifiant par type pour un compte, et une même valeur/type ne peut pas rattacher plusieurs comptes.
- Index sur `cases(subject_ref, created_at)`, `cases(status, updated_at)`, `registry_requests(status, updated_at)` et `audit_events(subject_ref, occurred_at)`.
- Clés étrangères avec `RESTRICT` pour les entités de configuration utilisées et `CASCADE` uniquement pour les tables d’association de portée (ex. `consent_questions`). Ne pas supprimer en cascade un dossier ou un événement d’audit.

## Hors du premier schéma

Pas de fiche centrale `citizens` contenant les attributs d’état civil, pas de copie des registres et pas de stockage d’image CNIB, d’acte ou de casier. Les références sont facultatives, déclaratives et propres au jeu fictif de démonstration. `CITIZEN_IDENTIFIER_ENCRYPTION_KEY` doit être définie avant d’enregistrer une référence ; sa rotation demande un rechiffrement contrôlé. La durée de conservation de ce lien, des références, dossiers, consentements et journaux doit être décidée avant l’usage de données réelles.

## Mise en route locale

Depuis `backend/`, après avoir démarré PostgreSQL avec `docker compose up -d postgres` à la racine :

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend .venv/bin/python -m scripts.seed_demo
DATABASE_URL=postgresql+psycopg://dlnuf:dlnuf-dev@localhost:55432/backend REGISTRY_ROUTES_FILE=../interoperability/connectors/routing.local.yaml .venv/bin/uvicorn app.main:app --reload
```

L’URL locale vise le port publié par Compose. Dans le conteneur backend, utiliser le nom de service `postgres` et le port interne `5432`. L’API expose `GET /health` et ses routes métier `/v1` via FastAPI, avec les sessions SQLAlchemy fournies par `SessionLocal` / `get_db`.
