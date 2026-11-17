# Frontend — Dites-le-nous une fois

Next.js, React, TypeScript et Tailwind CSS. Références : [interfaces](../docs/interfaces%283%29.md) et [organisation du dépôt](../docs/organisation_equipe_architecture_repository.md).

## Démarrer et vérifier

Depuis `frontend/` :

```bash
npm ci
npm run dev
npm run lint
npm run build
```

Application : http://localhost:3000. Sous PowerShell, utiliser `npm.cmd` si `npm.ps1` est bloqué. La compilation télécharge actuellement les polices Geist depuis Google Fonts.

## Espaces indépendants

| Groupe de routes | Dossier métier | URL prévue | Contenu |
|---|---|---|---|
| `app/(auth)/` | `features/auth/` | `/` | Accès unique par numéro ; `/inscription` redirige vers `/` |
| `app/(citizen)/usager/` | `features/citizen/` | `/usager` | Historique des consultations ; demande d’accord uniquement lorsqu’elle est en attente |
| `app/(agent)/guichet/` | `features/agent/` | `/guichet` | Identification, ouverture et suivi des dossiers, accord au guichet ou à distance, vérifications |
| `app/(trust-center)/centrale/` | `features/trust-center/` | `/centrale/...` | Conventions, état du réseau, contestations |
| `app/(administration)/administration/` | `features/administration/` | `/administration/...` | Registres locaux, services, conventions, journal |

Les espaces centrale et administration sont réservés par des `.gitkeep` : leurs écrans ne sont pas encore implémentés. Leurs URL sont des conventions pour les futures pages. Le portail citoyen et le guichet agent utilisent des données fictives et des échanges locaux, sans connexion au backend. Les groupes entre parenthèses organisent le code sans apparaître dans les URL ; les préfixes explicites évitent les collisions entre écrans.

## Organisation du code

- `app/` : routes et layouts. Les `page.tsx` composent les écrans métier.
- `app/globals.css` : thème, variables et styles de base uniquement.
- `features/<espace>/screens/` : écrans propres à cet espace.
- `features/<espace>/components/` : composants spécifiques.
- `features/<espace>/hooks/` : état et logique d'interaction.
- `features/<espace>/mocks/` : simulations isolées.
- `features/<espace>/styles/` : styles limités à cet espace.
- `components/shared/` : éléments communs, dont le bandeau Flash info.
- `components/ui/` : primitives UI génériques.
- `styles/` : styles des éléments communs.
- `lib/` : utilitaires indépendants des espaces.

L'authentification et le guichet agent disposent de leurs propres composants, hooks et mocks. L'adaptateur des dossiers est dans `features/agent/services/agent-cases.ts`, ses modèles dans `features/agent/types/`. Les échanges de démonstration entre espaces passent par `lib/demo-authorizations.ts` et `lib/demo-consultations.ts` ; aucun espace n'importe le code métier d'un autre.

## Ajouter un écran sans mélanger les espaces

1. Créer l'écran et ses composants dans `features/<espace>/`.
2. Créer un `page.tsx` léger dans le groupe de routes correspondant.
3. Ajouter le layout et les styles propres à cet espace : CSS Modules ou sélecteurs limités à son conteneur. L'authentification utilise `.auth-space`.
4. Partager uniquement les briques génériques dans `components/shared`, `components/ui` ou `lib`.

ESLint interdit les imports entre espaces et les dépendances des briques partagées vers un espace. Les fonctionnalités ne doivent pas importer les routes de `app/`. Vérification : `npm run lint`.

Cette séparation ne remplace pas le contrôle d'accès : les permissions devront être validées côté serveur lors de l'intégration Keycloak/backend.

## Guichet agent de démonstration

Depuis l'entrée http://localhost:3000, saisir **22222222**, puis **1234** : ce compte de démonstration ouvre `/guichet`. Le profil représente le guichet passeports de la DIPF. Seule la démarche `passeport_ordinaire_precheck`, appartenant à cette administration dans le catalogue backend, est proposée.

1. « Nouveau dossier » : saisir l'identifiant unique du citoyen et son téléphone national à huit chiffres. La recherche retrouve le profil fictif et vérifie que le téléphone saisi lui correspond avant d'autoriser l'ouverture du dossier.
2. Choisir la réponse au guichet ou à distance, puis ouvrir le dossier. Aucun registre n'est interrogé à cette étape. Un dossier actif existant est réutilisé pour éviter un doublon.
3. Sur place : envoyer un code, puis saisir celui communiqué par le citoyen. Le volet « SMS de démonstration » contient le code propre à ce dossier et le texte décrivant les vérifications autorisées. Le code expire après cinq minutes ; le renvoi est limité à une fois toutes les trente secondes. Ce n'est pas le PIN personnel du citoyen.
4. À distance : se connecter à l'espace citoyen dans un autre onglet du même navigateur. La réponse acceptée ou refusée remonte au guichet. Pour Awa, utiliser `11111111 / 0000`. Les autres numéros passent par la première connexion.
5. Lancer les vérifications après l'accord. Les résultats sont minimisés ; une indisponibilité et une identité ambiguë ne deviennent jamais un « non ». Les appels tentés apparaissent aussi dans l'historique du citoyen correspondant.

| Identifiant unique fictif | Contact | Scénario |
|---|---|---|
| `BF-00000001` | `11111111` | Parcours standard |
| `BF-00000002` | `44444444` | Justice indisponible au premier essai, puis reprise |
| `BF-00000003` | `33333333` | Nationalité ambiguë, examen humain nécessaire |

Ces identifiants posent l'hypothèse d'un identifiant citoyen unique partagé. Ils sont fictifs, sans valeur officielle. L'adaptateur frontend les associe aux anciens pivots d'acte des jeux de données ; les contrats partagés et le backend ne sont pas modifiés. Les anciens dossiers stockés dans le navigateur restent lisibles.

La liste du guichet est un tableau : dossier, identifiant citoyen, téléphone, démarche, mode d'accord, état, date de création et actions. Les icônes de détail et de traitement apparaissent au survol ou au focus clavier ; elles restent visibles sur écran tactile et sur petit écran. Le tableau peut défiler horizontalement sans élargir la page. Les raccourcis ouvrent la section concernée sans lancer automatiquement de consultation.

En cas d'indisponibilité, le guichet ouvert tente une reprise après quinze secondes ; une reprise manuelle est aussi possible. Les vérifications terminées ne sont pas rejouées. Un accord expiré ou refusé bloque les nouvelles consultations. « Vérifications terminées » ne signifie pas que le passeport est délivré : les pièces physiques et la décision restent à l'administration.

Les dossiers, accords et métadonnées de consultation sont persistés dans le stockage local de ce navigateur ; le contexte citoyen est propre à chaque onglet. Les codes temporaires restent en mémoire et doivent être redemandés après un rechargement. Les échanges entre appareils ne sont pas implémentés. Il n'existe ni contrôle d'accès réel ni journal infalsifiable dans cette simulation.

Pour l'intégration : utiliser l'API décrite dans `docs/api-documentation.md` avec des jetons Keycloak adaptés à chaque rôle. Le backend actuel exige le rôle citoyen pour répondre au consentement : le recueil d'un accord assisté par code nécessite un endpoint de preuve dédié, et ne doit pas être remplacé par un appel avec le jeton agent. Aucun contrat ni endpoint backend n'a été modifié ici.

## Accès citoyen actuel

L'écran initial affiche uniquement le numéro national à huit chiffres et « Continuer ».

- Numéro connu : saisie du PIN, puis ouverture de l'espace correspondant. Citoyen : **11111111 / 0000** → `/usager`. Agent : **22222222 / 1234** → `/guichet`. Le numéro agent est réservé et ne passe pas par la création d'un profil citoyen.
- Nouveau numéro : OTP de démonstration **123456**, valable cinq minutes, avec renvoi après trente secondes. Après validation, les cases OTP sont remplacées par une coche verte et les champs PIN/confirmation. La définition du PIN ouvre ensuite `/usager`.
- Les profils de démonstration créés sont mémorisés dans ce navigateur : aux connexions suivantes, seul le PIN est demandé après le numéro. Le stockage local conserve un sel et une empreinte PBKDF2 du PIN, jamais le PIN en clair. Effacer les données du navigateur efface ces profils.

Aucun SMS n'est envoyé et aucune session serveur n'est créée. Le portail reste un aperçu public avec des données fictives. La reconnaissance du numéro, l'OTP et la validation du PIN devront être réalisés par le backend / Keycloak pour un accès réel. Cette simulation locale nécessite un contexte sécurisé (HTTPS ou localhost) et le stockage local du navigateur.
