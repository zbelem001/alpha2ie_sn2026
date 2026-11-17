# API métier

Le contrat OpenAPI partagé est `contracts/openapi/backend.yaml`. Toutes les routes métier exigent un jeton Bearer émis par Keycloak. Les rôles `agent` et `citizen` sont contrôlés ; l’agent est limité à son administration et le citoyen à ses propres dossiers. Le contrat fixe le premier flux MVP :

1. `GET /v1/procedures` — afficher le catalogue de démarches/questionnaires.
2. `POST /v1/cases` — créer un dossier et ses vérifications prévues, sans appeler les registres.
3. `POST /v1/cases/{case_id}/consent` — enregistrer le consentement groupé, limité aux questions du dossier.
4. `POST /v1/cases/{case_id}/checks` — vérifier droits et consentement, appeler les connecteurs et enregistrer les résultats minimisés ; le même endpoint permet une reprise.
5. `GET /v1/cases/{case_id}` — consulter l’état global et par vérification.
6. `GET /v1/cases/{case_id}/journal` — fournir les événements métier lisibles par l’usager.
7. `DELETE /v1/cases/{case_id}/consent` — révoquer le consentement actif et bloquer les appels non encore envoyés.

Les réponses des registres suivent `contracts/schemas/registry-response.json`. L’API métier n’expose jamais le corps brut d’une réponse. Une indisponibilité laisse la vérification relançable ; la relance incrémente le compteur de tentative sans créer une nouvelle vérification logique. La demande est revendiquée atomiquement avant l’appel au registre, ce qui empêche deux exécutions concurrentes d’envoyer le même contrôle. Une revendication restée `pending` est considérée abandonnée après 60 secondes et peut alors être reprise ; l’ancienne tentative est clôturée avant la nouvelle.

Un nouveau choix du citoyen remplace tout accord précédent pour le dossier : un refus révoque les accords antérieurs. Sans `expires_at`, l’accord expire après 30 jours ; une date fournie doit inclure un fuseau horaire et se situer dans les 30 jours suivants.

Le catalogue de démonstration expose deux parcours :

Le processus d’ajout d’un parcours au catalogue est décrit dans le [guide d’ajout d’une démarche](guide-ajout-demarche.md).

- `concours_direct_preverification` contrôle le seuil minimum de 18 ans et la nationalité ; l’indicateur de casier est facultatif et doit être examiné par un agent. Le scénario ne vérifie pas le plafond d’âge, les dérogations ni les conditions propres à un concours donné. Les pièces et critères exacts restent ceux de l’avis officiel du concours concerné, conformément aux [conditions générales publiées par le ministère](https://www.fonction-publique.gov.bf/accueil/actualites/details?cHash=c95e568d76f3c9794f1783abc745a4c7&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=2273) et à l'[avis du concours ciblé](https://www.fonction-publique.gov.bf/fileadmin/user_upload/storage/fichiers/WW_A36-_CD_SF_2025_CONCOURS_MFPTPS.pdf).
- `passeport_ordinaire_precheck` couvre le dossier d’un demandeur majeur : vérifie la CNIB via le registre ONI simulé, retrouve l’acte d’état civil, vérifie la nationalité et la disponibilité d’un bulletin de casier en cours de validité auprès de Justice, puis vérifie le paiement du timbre fiscal requis via le Trésor simulé. Le bulletin est vérifié pour sa validité, pas pour l’absence de condamnation. Photos, justificatif de profession, dépôt physique et décision restent à l’administration. La composition est celle de la [Police nationale, autorité de délivrance](https://police.gov.bf/index.php/infos-utiles/passeport). Les registres ONI/Justice et paiements de ce prototype sont simulés ; aucun service réel n’est interrogé.

Le parcours concours interroge également Justice sur un indicateur de casier. Cet indicateur reste facultatif dans son calcul global et soumis à l’examen d’un agent : le mock ne modélise pas les seuils de condamnation et exceptions prévus par les textes. Pour le passeport adulte, c’est la validité du bulletin qui est contrôlée, indépendamment de son contenu.

Pour les deux parcours, `completed` signifie que les contrôles requis configurés ont abouti ; ce n’est pas une décision d’admission ou de délivrance.

Le realm `dlnuf` est importé par Docker Compose à partir de `infrastructure/keycloak/dlnuf-realm.json`. L’API vérifie la signature RS256 via le JWKS Keycloak, l’émetteur, l’audience, l’expiration et le client autorisé (`azp`). Comptes locaux de démonstration : `agent-demo` / `AgentDemo-2026!` (agent Fonction publique), `agent-passeport-demo` / `PassportDemo-2026!` (agent Direction de l’Immigration et de la Police des Frontières) et `citoyen-demo` / `CitoyenDemo-2026!` (rôle citoyen, identifiant fictif `ACTE:OUAGA:2004:01234`). Ces identifiants sont réservés à l’environnement local ; les mots de passe doivent être remplacés avant tout déploiement partagé.

Pour obtenir un jeton de démonstration :

```bash
curl -X POST http://localhost:8180/realms/dlnuf/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=dlnuf-api&username=agent-demo&password=AgentDemo-2026%21'
```

Copier `access_token` dans Swagger (`Authorize`) ou dans l’en-tête `Authorization: Bearer <token>`. Le flux Resource Owner Password Credentials sert ici uniquement aux essais locaux ; le frontend devra utiliser Authorization Code avec PKCE.
