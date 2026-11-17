> **Couche espace usager** (obligatoire, carte du jury). Responsable : Personne 1.
> Copie de `frontend/` (branche `mirror-project`) ; le dossier d'origine reste en place.
> Priorité de la carte : l'usager lance une démarche, voit le résultat et retrouve chaque consultation dans son espace (fin de la vidéo imposée).
> L'application contient encore le guichet agent (`src/app/(agent)`, couche bonus [guichet-agent](../guichet-agent/README.md)) et l'administration locale. Dans le texte ci-dessous, « depuis `frontend/` » se lit « depuis `espace-usager/` ».

# Frontend — Dites-le-nous une fois

Next.js, React, TypeScript et CSS Modules. Références : [interfaces](../docs/interfaces%283%29.md), [architecture](../docs/organisation_equipe_architecture_repository.md) et [ajout d’une démarche](../docs/guide-ajout-demarche.md).

## Démarrer et vérifier

Depuis `frontend/` : `npm ci`, `npm run dev`, `npm run lint`, `npm run build`. Sous PowerShell, utiliser `npm.cmd` si les scripts PowerShell sont bloqués.

Application : http://localhost:3000.

| Espace | Connexion de démonstration | Route |
|---|---|---|
| Citoyen | 11111111 / 0000 | /usager |
| Agent | 22222222 / 1234 | /guichet |
| Administrateur local | 99999999 / 1234 | /administration |

Un nouveau numéro national à huit chiffres passe par l’OTP fictif 123456, puis définit son PIN. Le PIN est mémorisé sous forme d’empreinte PBKDF2 avec sel. Aucun SMS réel ni session serveur n’est créé. Les comptes agents ajoutés dans la console utilisent la connexion habituelle ; la suspension refuse les connexions futures.

## Références propres à chaque registre

Il n’existe plus d’identifiant citoyen universel dans le frontend. Le numéro de téléphone sert à adresser une demande d’accord, pas à retrouver un document. Une référence de dossier reste un identifiant interne de suivi, sans valeur de pivot interadministrations.

L’administrateur associe chaque contrôle à un document du fournisseur concerné et précise l’aide à la saisie. Exemples : numéro de CNIB, référence d’acte de naissance (numéro, année et centre si nécessaires), certificat de nationalité, bulletin de casier, timbre fiscal ou déclaration de perte. Les libellés et exemples ne constituent pas des formats officiels validés. Les contrôles qui concernent le même document ne demandent sa référence qu’une fois.

Au guichet :

1. Choisir la démarche, saisir le téléphone et éventuellement le nom.
2. Sur place, demander et saisir uniquement les références configurées pour cette démarche avant d’ouvrir le dossier.
3. Envoyer un code d’accord valable cinq minutes, limité aux vérifications et références de cette demande. Toute modification des références invalide ce code. Le renvoi habituel reste limité à trente secondes.
4. Saisir le code communiqué par le citoyen, puis lancer les vérifications.
5. À distance, les références peuvent être complétées par le citoyen avant sa réponse.

Dans le portail citoyen, l’icône de profil dans l’en-tête ouvre l’écran dédié `/usager/profil`, qui permet de conserver facultativement ses références, de les modifier ou de les effacer en vidant les champs. Dans une demande d’accord, seules les références nécessaires apparaissent : les références déjà renseignées par l’agent sont prioritaires, puis celles du profil. Le citoyen peut les corriger, compléter les manquantes et choisir de les conserver dans son profil. Donner l’accord enregistre les références de la demande ; refuser ne nécessite aucune référence.

Le consentement porte sur un instantané des références. Elles ne peuvent plus être modifiées après la réponse. Changer le profil ne modifie pas les accords déjà donnés. Les vérifications sont bloquées sans références complètes, droit d’échange actif et accord valide. Les résultats et leurs reprises restent minimisés, et apparaissent dans l’historique citoyen sans recopier les numéros des documents.

Les anciens dossiers locaux restent lisibles. Les anciens accords sans références documentaires sur les dossiers non terminés repassent en attente de saisie et d’accord. Les anciens pivots ne sont pas utilisés pour retrouver les documents.

## Console locale

Menu : vue d’ensemble, dossiers, démarches, droits d’échange, registre et services, comptes agents, historique.

- Démarches : finalité, sélection et ordre des contrôles, document de recherche, aide à la saisie, caractère obligatoire ou facultatif, durée de l’accord (1 à 30 jours), brouillon et publication. Au moins un contrôle doit être obligatoire. Tous les contrôles obligatoires doivent être confirmés.
- Droits : demande d’accès ou suspension locale ; une demande reste en attente de validation par la gouvernance, sans auto-approbation.
- Registre : URL HTTP(S) sans secrets et test simulé de disponibilité. Services fournisseurs à réponse booléenne.
- Agents : création, suspension, réactivation et réinitialisation du PIN.
- Historique : date, acteur, rôle, action, cible et détail, avec recherche et filtres. Aucun PIN, code SMS ou numéro de document dans le journal des actions.
- Dossiers : les mêmes fonctions que l’agent. Chaque dossier conserve la version de ses contrôles et des documents attendus.

## Organisation

- `app/` : routes légères ; groupes `(auth)`, `(citizen)`, `(agent)`, `(administration)`.
- `features/<espace>/` : écrans, composants et styles propres à chaque rôle.
- `modules/casework/` : dossiers et contrôles communs à l’agent et à l’administrateur.
- `components/shared/` et `styles/` : bandeau Flash info et champs documentaires partagés.
- `lib/` : contrats locaux d’accord, références, profil documentaire, consultations et administration.
- La centrale reste à implémenter.

ESLint interdit les imports entre espaces et les dépendances des modules partagés vers un espace. Cette séparation ne remplace pas les contrôles d’accès serveur.

## Limites de la démonstration et intégration

Les données sont fictives, dans le stockage local du navigateur. Les onglets du même navigateur échangent leurs mises à jour ; les échanges entre appareils ne sont pas implémentés. Les codes temporaires restent en mémoire. Les routes sont des aperçus publics, sans permissions serveur ni journal infalsifiable. Les références enregistrées localement ne sont ni vérifiées ni chiffrées par un service de profil.

Les références sont utilisées pour délimiter l’accord et les contrôles simulés, sans appel réel aux registres. Les scénarios fictifs de disponibilité sont associés aux téléphones 44444444 (Justice indisponible au premier essai) et 33333333 (nationalité ambiguë). Les autres numéros suivent le parcours nominal. Cela ne constitue pas une recherche d’identité par téléphone.

Le backend actuel et ses contrats utilisent encore `subject.pivot_id`. Leur évolution vers des références distinctes par contrôle devra être coordonnée avec les connecteurs des registres : aucune modification backend ou de `contracts/` n’est incluse ici. L’intégration nécessite également Keycloak, l’adressage sécurisé des demandes au citoyen, la preuve de consentement assisté, les comptes agents, la validation des conventions et un stockage de profil protégé. Le backend actuel exige le rôle citoyen pour répondre à un consentement ; ne pas remplacer la preuve assistée par le jeton de l’agent.

« Vérifications terminées » signifie que les contrôles requis ont abouti ; la décision administrative reste à l’administration.
