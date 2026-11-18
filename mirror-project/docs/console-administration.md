# Console d’administration locale

L’interface de `main` est réutilisée dans `administration/src/features/administration/`, avec ses panneaux et ses styles. Elle est disponible sur `http://localhost:3002/administration`.

Les simulations locales ont été remplacées par `src/lib/administration-api.ts`, qui appelle les routes `/v1/admin/*` par le relais serveur. Les jetons restent dans les cookies `httpOnly` et le backend limite les ressources à l’administration du compte connecté.

## Accès

Un compte Keycloak avec numéro national comme identifiant, PIN et rôle `local-admin` est redirigé vers la console après connexion. Il doit porter un `administration_code` valide. Le rôle administrateur est attribué par l’opérateur habilité, jamais par l’inscription publique. Aucun compte administrateur préconfiguré n’est proposé dans le formulaire.

Les agents continuent d’ouvrir `/guichet` et sont refusés sur les routes `/api/backend/admin/*` par le relais et sur `/v1/admin/*` par le backend. Les administrateurs peuvent aussi utiliser le guichet depuis l’entrée « Dossiers ».

## Fonctions reprises

- Vue d’ensemble des données renvoyées par l’API ; le compteur de dossiers concerne les dossiers récents chargés, pas un total paginé exhaustif.
- Dossiers et consentement : même module et même API que le guichet agent.
- Démarches : catalogue, brouillon, publication, activation et contrôles documentaires. Le type de document est fixé par le contrôle côté serveur. Une démarche déjà utilisée est verrouillée par l’API ; créer une autre démarche pour changer son périmètre.
- Droits d’échange : demande en attente de validation et suspension locale ; aucune auto-approbation.
- Registre et services : configuration de l’URL et déclaration des services booléens proposés.
- Agents : création avec PIN à six chiffres, suspension, réactivation et réinitialisation du PIN dans Keycloak. Le client de service doit être configuré comme décrit dans `acces-telephone.md`.
- Historique : actions enregistrées par le serveur, recherche et filtre par acteur, sans afficher de PIN ni de code OTP.

## Limite importante du raccordement

Le test du registre reste **simulé** car c’est le comportement actuel de l’API. Déclarer une URL ou un service ne met pas à jour automatiquement le routage direct, le banc X-Road, les certificats ou ses conventions. L’écran indique cette distinction et ne présente pas une déclaration comme une preuve de connexion.

La console ne centralise pas les données des registres et ne propose pas d’import de fichiers citoyens. Les données restent dans les registres des administrations.
