# API métier

Le contrat OpenAPI partagé est `contracts/openapi/backend.yaml`. Il fixe le premier flux MVP :

1. `GET /v1/procedures` — afficher le catalogue de démarches/questionnaires.
2. `POST /v1/cases` — créer un dossier et ses vérifications prévues, sans appeler les registres.
3. `POST /v1/cases/{case_id}/consent` — enregistrer le consentement groupé, limité aux questions du dossier.
4. `POST /v1/cases/{case_id}/checks` — vérifier droits et consentement, appeler les connecteurs et enregistrer les résultats minimisés ; le même endpoint permet une reprise.
5. `GET /v1/cases/{case_id}` — consulter l’état global et par vérification.
6. `GET /v1/cases/{case_id}/journal` — fournir les événements métier lisibles par l’usager.
7. `DELETE /v1/cases/{case_id}/consent` — révoquer le consentement actif et bloquer les appels non encore envoyés.

Les réponses des registres suivent `contracts/schemas/registry-response.json`. L’API métier n’expose jamais le corps brut d’une réponse. Une indisponibilité conserve la vérification en attente ; la relance incrémente le compteur de tentative sans créer une nouvelle vérification logique.

Le contrat décrit les formats et statuts, mais l’authentification/autorisation HTTP n’est pas encore intégrée aux routes : elle devra être raccordée à Keycloak avant d’exposer les opérations à un réseau autre que le poste de développement.
