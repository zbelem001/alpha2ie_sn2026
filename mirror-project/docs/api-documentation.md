# API métier

## Routes de la console d’administration

Les routes `/v1/admin/*` sont réservées à un jeton Keycloak avec le rôle `local-admin` et un `administration_code` actif. Les ressources sont toujours limitées à cette administration. `GET /v1/admin/config` fournit l’agrégat utilisé par la console : démarches, demandes de droits, registre, services déclarés et agents.

- `PUT /v1/admin/procedures/{code}` crée ou met à jour un brouillon. La publication est refusée si un droit d’échange n’est pas approuvé. Une démarche déjà utilisée par un dossier est verrouillée : créez une nouvelle démarche pour ne pas changer rétroactivement le périmètre des dossiers existants.
- `PATCH /v1/admin/procedures/{code}/active` active ou suspend une démarche publiée.
- `POST /v1/admin/rights/{question_code}/request` consigne une demande en attente ; une demande ne donne aucun accès. `POST /v1/admin/rights/{question_code}/suspend` coupe l’autorisation locale d’une permission approuvée. L’approbation de convention reste une décision de gouvernance hors de la console locale.
- `PUT /v1/admin/registry` enregistre le nom et l’URL sans identifiant ni secret. `POST /v1/admin/registry/test` reste explicitement simulé et n’appelle pas l’URL.
- `POST /v1/admin/services` déclare un service booléen et `PATCH /v1/admin/services/{id}/active` le désactive ou le réactive. La déclaration ne crée pas à elle seule un connecteur de registre.
- `GET/POST /v1/admin/agents`, `PATCH /v1/admin/agents/{id}/active` et `PUT /v1/admin/agents/{id}/pin` gèrent les utilisateurs dans Keycloak. Les PIN ne sont ni conservés dans la base métier ni ajoutés au journal.
- `GET /v1/admin/audit` regroupe les actions de la console et les événements de dossier de l’administration.

Pour les comptes agents, créer un client OIDC confidentiel de service dans le realm `dlnuf`. Le script de préparation lui attribue le rôle Keycloak `realm-management/manage-users`, requis pour créer et gérer les comptes, puis on fournit son secret dans `KEYCLOAK_ADMIN_CLIENT_SECRET` du `.env` et on lance une fois `docker compose --profile admin-setup run --rm keycloak-admin-client-init`. Keycloak donne à ce rôle une portée de gestion des utilisateurs du realm ; l’API vérifie aussi le code d’administration avant chaque opération. Gardez le secret côté serveur et ne donnez pas le rôle `realm-admin`. Sans ce secret, les autres réglages d’administration restent accessibles, mais la gestion d’agents retourne une indisponibilité.

Le realm local importe le compte de démonstration `admin-passeport-demo` avec le rôle `local-admin` et l’administration DIPF. Son mot de passe de développement est `AdminPasseport-2026!`; changez-le avant un environnement partagé. Le code PIN reçu lors de la création d’un agent devient son mot de passe Keycloak, avec son numéro national comme nom d’utilisateur.

Le contrat OpenAPI partagé est `contracts/openapi/backend.yaml`. Les routes métier exigent un jeton Bearer émis par Keycloak, sauf les deux routes publiques de vérification du téléphone avant inscription. Les rôles `agent`, `local-admin` et `citizen` sont contrôlés ; agents et administrateurs sont limités à leur administration, le citoyen à ses propres dossiers.

Pour la première inscription, `POST /v1/auth/registration/otp` crée un défi puis `POST /v1/auth/registration/otp/verify` valide le code. En mode `SMS_PROVIDER=simulated`, le backend n’envoie aucun SMS : il retourne un code de démo si `OTP_SIMULATION_EXPOSE_CODE=true`. Après validation du code, `phone_verified` vaut `true` pour permettre le parcours de démonstration; `verification_mode: "simulation"` et `phoneVerificationSimulated: true` signalent explicitement que ce résultat ne prouve pas la possession réelle du téléphone. La création de compte Keycloak n’est pas encore raccordée.

Le mode simulé est configuré dans le `.env` local : `SMS_PROVIDER=simulated`, `OTP_SIMULATION_EXPOSE_CODE=true` et une clé privée `OTP_SIMULATION_SECRET` d’au moins 32 caractères. Le code à six chiffres est dérivé par HMAC de la clé et de l’identifiant du défi; seule son empreinte est conservée en base. Il expire après cinq minutes, tolère au plus cinq essais et ne peut être validé qu’une fois. Le code n’est retourné qu’en mode simulé. En mode réel, `SMS_PROVIDER=infobip` continue d’utiliser les défis 2FA Infobip.

Le contrat fixe aussi le flux dossier suivant :

1. `GET /v1/procedures` — afficher le catalogue de démarches/questionnaires.
2. `GET /v1/citizen/identifiers` et `PUT /v1/citizen/identifiers` — rattacher le compte citoyen et gérer les identifiants de documents facultatifs.
3. `POST /v1/cases` — créer un dossier et ses vérifications prévues, sans appeler les registres; choisir `consent_channel: "web"` ou `"assisted"`.
4. `GET /v1/cases` — lister les dossiers visibles par le compte : ceux de son administration pour un agent, les siens pour un citoyen. `GET /v1/cases/{case_id}` retourne un dossier précis.
5. `POST /v1/cases/{case_id}/consent/request` — l’agent change le canal entre `web` et `assisted`. La demande est réémise et tout OTP actif est invalidé. Un consentement déjà accordé doit d’abord être révoqué par le citoyen.
6. `POST /v1/cases/{case_id}/consent/otp` et `/consent/otp/verify` — envoyer puis valider le code d’un consentement assisté au guichet. En simulation, aucun SMS n’est envoyé, le code de démo est retourné et la réponse porte `mode: "simulation"`.
7. `POST /v1/cases/{case_id}/consent` — enregistrer la réponse du citoyen, limitée aux questions du dossier. Un refus peut être fait depuis le portail pour les deux canaux ; un accord `assisted` exige la vérification OTP dédiée.
8. `POST /v1/cases/{case_id}/checks` — vérifier droits et consentement, appeler les connecteurs et enregistrer les résultats minimisés ; le même endpoint permet une reprise.
9. `GET /v1/cases/{case_id}/journal` — fournir les événements métier lisibles par l’usager.
10. `DELETE /v1/cases/{case_id}/consent` — révoquer le consentement actif et bloquer les appels non encore envoyés.
11. `GET /v1/notifications` et `POST /v1/notifications/{notification_id}/read` — consulter et marquer comme lue une alerte de la plateforme destinée au citoyen connecté.

À la première connexion, le frontend peut appeler `PUT /v1/citizen/identifiers` avec `confirmed: true` et zéro à huit identifiants disponibles. Types acceptés : `cnib_number`, `birth_act_number`, `criminal_record_number`, `nationality_reference`, `payment_reference` et `loss_report_number`. Chaque référence est facultative ; le citoyen peut mettre à jour sa liste. Le numéro de téléphone du compte, au format international, est requis pour rattacher le compte et adresser les SMS, mais les identifiants de documents ne sont pas validés comme preuves d’identité : ce sont des références fictives et déclaratives pour la démo. Le pivot interne `CITIZEN:<UUID>` ne constitue pas un identifiant officiel. L’ancien endpoint `POST /v1/citizen/identity-link` reste disponible pour les scénarios de démonstration utilisant `ACTE:...`.

Les références de documents sont chiffrées en base avec `CITIZEN_IDENTIFIER_ENCRYPTION_KEY`; les recherches utilisent une empreinte HMAC, pas la valeur en clair. Générer la clé locale avec `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` et la conserver dans le `.env` non versionné. Toute rotation exige de rechiffrer les valeurs existantes avant de remplacer la clé.

Exemple de références déclarées lors de la première connexion (le citoyen n’envoie que celles qu’il possède) :

```json
{
  "confirmed": true,
  "identifiers": [
    {"identifier_type": "cnib_number", "value": "CNIB-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "birth_act_number", "value": "ACTE-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "criminal_record_number", "value": "CASIER-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "nationality_reference", "value": "NAT-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "payment_reference", "value": "PAY-2026-0004"}
  ]
}
```

Pour créer une démarche, l’agent peut fournir `citizen_identifier: {identifier_type, value}` ou le numéro de téléphone lié au compte (`phone_number` ou `phone`) afin de retrouver le citoyen. Les références des registres peuvent être envoyées sous `registry_identifiers` (format API) ou `references` (format frontend, clés `cnib`, `birth`, `nationality`, `criminal`, `payment`, `loss`). Les références enregistrées au profil sont reprises automatiquement si l’agent ne fournit pas de remplacement. Les dossiers renvoient les champs de compatibilité frontend en camelCase (`procedureCode`, `createdAt`, `procedureTitle`, `checks[].questionCode`, `attemptCount`) tout en conservant les champs snake_case de l’API. Un identifiant absent laisse le contrôle correspondant bloqué et aucun appel n’est fait à ce registre. Le citoyen peut compléter sa liste puis l’agent relance `POST /v1/cases/{case_id}/checks` avec le consentement toujours actif. Les appels ne partent qu’après consentement actif couvrant la question. Les réponses des mocks restent minimisées (`valid`, `found`, `burkinabe`, `paid`, etc.) et ne renvoient pas les numéros de documents.

Exemple de création d’un dossier passeport :

```json
{
  "procedure_code": "passeport_ordinaire_precheck",
  "consent_channel": "web",
  "phone_number": "+22670000000",
  "citizen_identifier": {"identifier_type": "cnib_number", "value": "CNIB-DEMO-OUAGA-2004-01234"},
  "registry_identifiers": [
    {"identifier_type": "birth_act_number", "value": "ACTE-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "nationality_reference", "value": "NAT-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "criminal_record_number", "value": "CASIER-DEMO-OUAGA-2004-01234"},
    {"identifier_type": "payment_reference", "value": "PAY-2026-0004"}
  ]
}
```

À l’ouverture d’un dossier en mode `web`, le backend crée une alerte plateforme et envoie un SMS simple personnalisé. Son modèle se trouve dans `backend/app/sms_templates.py`. En mode `assisted`, l’agent envoie le PIN Infobip par `POST /v1/cases/{case_id}/consent/otp`, puis vérifie le code communiqué par le citoyen avec `POST /v1/cases/{case_id}/consent/otp/verify`. Le numéro retourné à l’agent est masqué. Le backend garde le `pinId` Infobip, jamais le PIN lui-même; Infobip effectue la vérification. L’envoi est limité à cinq codes par dossier et par heure, avec 30 secondes entre les renvois. La route de consentement web refuse les dossiers `assisted` pour qu’ils ne contournent pas la vérification OTP.

Configuration `.env` : `INFOBIP_OTP_API_KEY` sert aux OTP d’inscription et de consentement; `INFOBIP_SMS_API_KEY` sert aux SMS simples; `INFOBIP_BASE_URL`, `INFOBIP_SENDER` et `TEST_PHONE_NUMBER` complètent la configuration. Créer une application 2FA Infobip et deux modèles contenant `{{pin}}`, puis renseigner `INFOBIP_2FA_APPLICATION_ID`, `INFOBIP_2FA_REGISTRATION_MESSAGE_ID` et `INFOBIP_2FA_CONSENT_MESSAGE_ID`. Configurer l’application avec PIN à six chiffres, cinq essais et une durée de vie de cinq minutes. En compte d’essai, le numéro demandé doit être identique à `TEST_PHONE_NUMBER`, car le routage de démo n’envoie qu’à ce numéro.

Pour prévisualiser ou tester l’adaptateur SMS Infobip v3, depuis `backend/`, lancer `python -m scripts.test_infobip_sms --dry-run` ou `python -m scripts.test_infobip_sms`. Le script affiche le message final en prévisualisation, ou le `messageId` et le statut retournés après l’appel réel.

Les réponses des registres suivent `contracts/schemas/registry-response.json`. L’API métier n’expose jamais le corps brut d’une réponse. Une indisponibilité laisse la vérification relançable ; la relance incrémente le compteur de tentative sans créer une nouvelle vérification logique. La demande est revendiquée atomiquement avant l’appel au registre, ce qui empêche deux exécutions concurrentes d’envoyer le même contrôle. Une revendication restée `pending` est considérée abandonnée après 60 secondes et peut alors être reprise ; l’ancienne tentative est clôturée avant la nouvelle.

Un nouveau choix du citoyen remplace tout accord précédent pour le dossier : un refus révoque les accords antérieurs. Sans `expires_at`, l’accord expire après 30 jours ; une date fournie doit inclure un fuseau horaire et se situer dans les 30 jours suivants.

Le catalogue de démonstration expose deux parcours :

Le processus d’ajout d’un parcours au catalogue est décrit dans le [guide d’ajout d’une démarche](guide-ajout-demarche.md).

- `concours_direct_preverification` contrôle le seuil minimum de 18 ans et la nationalité ; l’indicateur de casier est facultatif et doit être examiné par un agent. Le scénario ne vérifie pas le plafond d’âge, les dérogations ni les conditions propres à un concours donné. Les pièces et critères exacts restent ceux de l’avis officiel du concours concerné, conformément aux [conditions générales publiées par le ministère](https://www.fonction-publique.gov.bf/accueil/actualites/details?cHash=c95e568d76f3c9794f1783abc745a4c7&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=2273) et à l'[avis du concours ciblé](https://www.fonction-publique.gov.bf/fileadmin/user_upload/storage/fichiers/WW_A36-_CD_SF_2025_CONCOURS_MFPTPS.pdf).
- `passeport_ordinaire_precheck` couvre le dossier d’un demandeur majeur : vérifie la CNIB via le registre ONI simulé, retrouve l’acte d’état civil, vérifie la nationalité et la disponibilité d’un bulletin de casier en cours de validité auprès de Justice, puis vérifie le paiement du timbre fiscal requis via le Trésor simulé. Le bulletin est vérifié pour sa validité, pas pour l’absence de condamnation. Photos, justificatif de profession, dépôt physique et décision restent à l’administration. La composition est celle de la [Police nationale, autorité de délivrance](https://police.gov.bf/index.php/infos-utiles/passeport). Les registres ONI/Justice et paiements de ce prototype sont simulés ; aucun service réel n’est interrogé.

Le parcours concours interroge également Justice sur un indicateur de casier. Cet indicateur reste facultatif dans son calcul global et soumis à l’examen d’un agent : le mock ne modélise pas les seuils de condamnation et exceptions prévus par les textes. Pour le passeport adulte, c’est la validité du bulletin qui est contrôlée, indépendamment de son contenu.

Pour les deux parcours, `completed` signifie que les contrôles requis configurés ont abouti ; ce n’est pas une décision d’admission ou de délivrance.

Le realm `dlnuf` est importé par Docker Compose à partir de `infrastructure/keycloak/dlnuf-realm.json`. L’API vérifie la signature RS256 via le JWKS Keycloak, l’émetteur, l’audience, l’expiration et le client autorisé (`azp`). Comptes locaux de démonstration : `agent-demo` / `AgentDemo-2026!` (agent Fonction publique), `agent-passeport-demo` / `PassportDemo-2026!` (agent Direction de l’Immigration et de la Police des Frontières) et `citoyen-demo` / `CitoyenDemo-2026!` (rôle citoyen, référence à rattacher à la première connexion). Ces identifiants sont réservés à l’environnement local ; les mots de passe doivent être remplacés avant tout déploiement partagé.

Pour obtenir un jeton de démonstration :

```bash
curl -X POST http://localhost:8180/realms/dlnuf/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=dlnuf-api&username=agent-demo&password=AgentDemo-2026%21'
```

Copier `access_token` dans Swagger (`Authorize`) ou dans l’en-tête `Authorization: Bearer <token>`. Le flux Resource Owner Password Credentials sert ici uniquement aux essais locaux ; le frontend devra utiliser Authorization Code avec PKCE.
