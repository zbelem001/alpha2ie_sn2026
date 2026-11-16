# API métier

Le contrat OpenAPI partagé est `contracts/openapi/backend.yaml`. Toutes les routes métier exigent un jeton Bearer émis par Keycloak. Les rôles `agent` et `citizen` sont contrôlés ; l’agent est limité à son administration et le citoyen à ses propres dossiers. Le contrat fixe le premier flux MVP :

1. `GET /v1/procedures` — afficher le catalogue de démarches/questionnaires.
2. `POST /v1/cases` — créer un dossier et ses vérifications prévues, sans appeler les registres.
3. `POST /v1/cases/{case_id}/consent` — enregistrer le consentement groupé, limité aux questions du dossier.
4. `POST /v1/cases/{case_id}/checks` — vérifier droits et consentement, appeler les connecteurs et enregistrer les résultats minimisés ; le même endpoint permet une reprise.
5. `GET /v1/cases/{case_id}` — consulter l’état global et par vérification.
6. `GET /v1/cases/{case_id}/journal` — fournir les événements métier lisibles par l’usager.
7. `DELETE /v1/cases/{case_id}/consent` — révoquer le consentement actif et bloquer les appels non encore envoyés.

Les réponses des registres suivent `contracts/schemas/registry-response.json`. L’API métier n’expose jamais le corps brut d’une réponse. Une indisponibilité conserve la vérification en attente ; la relance incrémente le compteur de tentative sans créer une nouvelle vérification logique.

Le realm `dlnuf` est importé par Docker Compose à partir de `infrastructure/keycloak/dlnuf-realm.json`. L’API vérifie la signature RS256 via le JWKS Keycloak, l’émetteur, l’audience, l’expiration et le client autorisé (`azp`). Comptes locaux de démonstration : `agent-demo` / `AgentDemo-2026!` (rôle agent, Fonction publique) et `citoyen-demo` / `CitoyenDemo-2026!` (rôle citoyen, identifiant fictif `ACTE:OUAGA:2004:01234`). Ces identifiants sont réservés à l’environnement local ; les mots de passe doivent être remplacés avant tout déploiement partagé.

Pour obtenir un jeton de démonstration :

```bash
curl -X POST http://localhost:8180/realms/dlnuf/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=dlnuf-api&username=agent-demo&password=AgentDemo-2026%21'
```

Copier `access_token` dans Swagger (`Authorize`) ou dans l’en-tête `Authorization: Bearer <token>`. Le flux Resource Owner Password Credentials sert ici uniquement aux essais locaux ; le frontend devra utiliser Authorization Code avec PKCE.
