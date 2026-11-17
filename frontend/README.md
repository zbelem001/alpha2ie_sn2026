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
| `app/(auth)/` | `features/auth/` | `/`, `/inscription` | Connexion et inscription existantes |
| `app/(citizen)/usager/` | `features/citizen/` | `/usager` | Historique des consultations ; demande d’accord uniquement lorsqu’elle est en attente |
| `app/(agent)/guichet/` | `features/agent/` | `/guichet/...` | Dossiers, identification, vérifications, attentes |
| `app/(trust-center)/centrale/` | `features/trust-center/` | `/centrale/...` | Conventions, état du réseau, contestations |
| `app/(administration)/administration/` | `features/administration/` | `/administration/...` | Registres locaux, services, conventions, journal |

Les espaces agent, centrale et administration sont réservés par des `.gitkeep` : leurs écrans ne sont pas encore implémentés. Leurs URL sont des conventions pour les futures pages. Le portail citoyen est une proposition utilisant des données fictives et des actions locales, sans connexion au backend. Les groupes entre parenthèses organisent le code sans apparaître dans les URL ; les préfixes explicites évitent les collisions entre écrans.

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

L'authentification dispose déjà de ces dossiers. Créer les sous-dossiers des autres espaces à mesure que leurs écrans sont développés. Placer les futurs clients API dans `features/<espace>/services/` et leurs types dans `features/<espace>/types/`.

## Ajouter un écran sans mélanger les espaces

1. Créer l'écran et ses composants dans `features/<espace>/`.
2. Créer un `page.tsx` léger dans le groupe de routes correspondant.
3. Ajouter le layout et les styles propres à cet espace : CSS Modules ou sélecteurs limités à son conteneur. L'authentification utilise `.auth-space`.
4. Partager uniquement les briques génériques dans `components/shared`, `components/ui` ou `lib`.

ESLint interdit les imports entre espaces et les dépendances des briques partagées vers un espace. Les fonctionnalités ne doivent pas importer les routes de `app/`. Vérification : `npm run lint`.

Cette séparation ne remplace pas le contrôle d'accès : les permissions devront être validées côté serveur lors de l'intégration Keycloak/backend.

## Parcours d'inscription actuel

Accès citoyen de démonstration depuis la connexion : numéro **11111111**, PIN **0000**. Une saisie valide ouvre `/usager`. Ce mock ne crée aucune session serveur ; le portail reste un aperçu public avec des données fictives.

Numéro national à huit chiffres, puis OTP de démonstration **123456**, valable cinq minutes, avec renvoi après trente secondes. Après validation, les cases OTP sont remplacées sur le même écran par une coche verte et les champs PIN/confirmation.

Aucun SMS n'est envoyé et aucun compte réel n'est créé : les contrats API métier et les services correspondants restent à connecter.
