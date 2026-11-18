# Accès par téléphone et PIN

Les deux applications reprennent le design sobre de `main` : motifs verts du login, bouton jaune, en-tête compact et Flash info masqué sur mobile. Les fonctionnalités connectées restent dans le miroir.

## Parcours

- Citoyen : numéro national à huit chiffres → Continuer. Un numéro connu demande le PIN. Un nouveau numéro reçoit un OTP serveur, puis choisit et confirme son PIN (4 à 6 chiffres). La validation remplace les cases OTP par une coche verte et les champs PIN. Un véritable utilisateur Keycloak avec le rôle citoyen est créé, puis connecté.
- Agent : numéro → PIN. Les comptes sont créés par l’administration ; cette interface ne crée pas de compte agent et ne transforme jamais un citoyen en agent.
- Aucun compte préconfiguré ni mot de passe de démonstration n’est affiché sur la connexion. Les sessions et le renouvellement restent en cookies `httpOnly`.
- Le citoyen consulte son historique et répond aux demandes ; le lancement autonome d’une démarche n’est plus proposé.

## Configuration serveur

Le serveur a besoin du client de service Keycloak (`KEYCLOAK_ADMIN_CLIENT_ID` et `KEYCLOAK_ADMIN_CLIENT_SECRET`). Générer un secret privé, le placer dans le `.env` ignoré par Git, puis exécuter :

```sh
docker compose --profile admin-setup run --rm keycloak-admin-client-init
docker compose up -d --build
```

Le client dispose de `manage-users` et `view-realm` pour créer le compte et lui attribuer uniquement le rôle citoyen. Aucun secret de service n’est transmis au navigateur. Le script de configuration du profil Keycloak rend les noms et l’e-mail facultatifs pour ce parcours téléphonique et active le ralentissement après plusieurs échecs de connexion.

La preuve d’inscription est signée avec `PHONE_REGISTRATION_SECRET` ou, à défaut, `OTP_SIMULATION_SECRET` (32 caractères minimum). Elle est liée au défi, au téléphone et à la validation OTP, expire avec le défi et n’est consommable qu’une fois. Elle n’est jamais un mécanisme de réinitialisation d’un PIN existant.

**Compte réel ne signifie pas SMS réel** : avec `SMS_PROVIDER=simulated`, l’OTP reste explicitement simulé et peut être affiché si `OTP_SIMULATION_EXPOSE_CODE=true`. Aucun numéro n’est déclaré vérifié par SMS dans Keycloak dans ce mode. Pour envoyer réellement le code, configurer le fournisseur SMS et ses identifiants serveur. Aucun code fixe n’est accepté par le frontend.

## Routes publiques ajoutées

| Route backend | Fonction |
|---|---|
| `POST /v1/auth/phone/continue` | Numéro connu : PIN ; nouveau citoyen : défi OTP |
| `POST /v1/auth/phone/verify` | Vérifie l’OTP et délivre une preuve courte d’inscription |
| `POST /v1/auth/phone/register` | Consomme la preuve et crée le compte citoyen Keycloak |

Les applications relaient ces opérations par `POST /api/auth/phone`. La connexion finale passe par `/api/auth/login`, qui accepte désormais un numéro national et un PIN. Les anciens comptes de test nommés ne passent plus par ce formulaire.

Les références documentaires, les droits d’accès et le rattachement avec preuve restent contrôlés par l’API métier. L’inscription téléphonique ne prouve pas la titularité d’un document et ne contourne pas ce contrôle.

Tests : preuve fausse, défi non vérifié, expiration et liaison au téléphone dans `demarches/tests/test_phone_auth.py`. Les anciens scénarios E2E fondés sur les comptes nommés et le formulaire identifiant/mot de passe nécessitent des fixtures de comptes téléphoniques avant réutilisation.
