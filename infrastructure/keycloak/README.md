# Keycloak : realm `dlnuf`

Responsable : Personne 3. Utilisé par le frontend (Personne 1) pour connecter les utilisateurs, et par le backend (Personne 2) pour vérifier les jetons.

Le realm est décrit dans [import/realm-dlnuf.json](import/realm-dlnuf.json) et importé automatiquement au premier `docker compose up`.

## Connexion : téléphone et code PIN

Pour coller à la page de connexion du frontend :

- **identifiant** : le numéro de téléphone en chiffres, sans `+` ni espaces (`+226 70 00 00 01` devient `22670000001`) ;
- **mot de passe** : le code PIN, de 4 à 6 chiffres (politique appliquée par Keycloak) ;
- après **5 échecs**, le compte est bloqué temporairement (60 s, puis de plus en plus longtemps, jusqu'à 15 min).

## Comptes de démonstration

PIN commun : `1234`. Valeurs fictives, à ne jamais réutiliser hors développement.

| Téléphone | Personne | Rôle | Attributs |
|---|---|---|---|
| `22670000001` | Awa KABORE | `usager` | pivot `ACTE:OUAGA:2004:01234`, niveau 2 |
| `22670000002` | Issa SAWADOGO | `usager` | pivot `ACTE:OUAGA:1998:00456`, niveau 2 |
| `22670000003` | Mariam OUATTARA | `usager` | pivot `ACTE:OUAGA:1997:00933`, niveau 3 |
| `22670000010` | Agent ONI | `agent` | administration `BF/GOV/ONI` |
| `22670000020` | Admin MAIRIE | `admin-local` | administration `BF/GOV/MAIRIE-OUAGA` |
| `22670000030` | Admin CENTRALE | `admin-centrale` | — |

Les identifiants pivots sont ceux des registres simulés : le parcours d'Awa est cohérent de la connexion jusqu'aux registres.

Console d'administration : http://localhost:8180/admin (identifiants `admin` / `admin-dev`, à changer dans `.env`).

## Contenu des jetons

Exemple de jeton d'accès d'Awa (extrait) :

```json
{
  "iss": "http://localhost:8180/realms/dlnuf",
  "aud": ["dlnuf-backend", "account"],
  "preferred_username": "22670000001",
  "name": "Awa KABORE",
  "roles": ["usager", "default-roles-dlnuf", "offline_access", "uma_authorization"],
  "identifiant_pivot": "ACTE:OUAGA:2004:01234",
  "niveau_garantie": 2
}
```

| Claim | Contenu | Présent pour |
|---|---|---|
| `roles` | Rôles du realm : `usager`, `agent`, `admin-local` ou `admin-centrale` (et des rôles techniques à ignorer) | Tous |
| `identifiant_pivot` | Référence de l'acte de naissance | Usagers |
| `niveau_garantie` | Entier, 1 à 3 | Usagers |
| `administration` | Identifiant X-Road de l'administration de rattachement | Agents, admins locaux |

Ces claims sont dans le jeton d'accès, l'ID token et `userinfo`. L'usager **ne peut pas** modifier son identifiant pivot, son niveau, son nom ni son administration : seul un administrateur le peut.

## Frontend (Personne 1)

Client : `dlnuf-frontend`, confidentiel. Le secret reste côté serveur Next.js, jamais dans le navigateur.

| Paramètre | Valeur en développement |
|---|---|
| Émetteur (issuer) | `http://localhost:8180/realms/dlnuf` |
| Client ID | `dlnuf-frontend` |
| Secret | `dev-frontend-secret-a-changer` |
| Adresses de retour autorisées | `http://localhost:3000/*` |

Deux façons de connecter le formulaire, les deux étant activées :

1. **Formulaire actuel (téléphone + PIN), le plus rapide.** Une route serveur Next.js envoie les identifiants au point d'accès des jetons :

   ```bash
   curl -s http://localhost:8180/realms/dlnuf/protocol/openid-connect/token \
     -d grant_type=password -d client_id=dlnuf-frontend \
     -d client_secret=dev-frontend-secret-a-changer \
     -d username=22670000001 -d password=1234 -d scope=openid
   ```

   La réponse contient `access_token` (à joindre aux appels du backend : `Authorization: Bearer …`), `id_token` et `refresh_token`. Ce mode (« password grant ») est déconseillé en production : l'application voit le PIN et ne profite pas des pages de Keycloak (second facteur, etc.). Il est acceptable pour le prototype, à condition que l'appel parte **du serveur** Next.js.

2. **Page de connexion de Keycloak (cible pour la production).** Redirection OpenID Connect avec PKCE, par exemple avec Auth.js et le fournisseur Keycloak. La maquette téléphone + PIN peut être reportée dans un thème Keycloak.

## Backend (Personne 2)

Vérifier chaque jeton reçu dans `Authorization: Bearer …` :

| Contrôle | Valeur |
|---|---|
| Signature | Clés publiques (RS256) : `http://keycloak:8080/realms/dlnuf/protocol/openid-connect/certs` depuis un conteneur, `http://localhost:8180/...` depuis la machine |
| `iss` | Toujours `http://localhost:8180/realms/dlnuf` |
| `aud` | Doit contenir `dlnuf-backend` |
| `exp` | Jeton valide 5 minutes |

Ensuite, lire `roles`, `identifiant_pivot`, `niveau_garantie` et `administration`.

L'émetteur ne dépend pas de l'endroit d'où l'on appelle Keycloak : il est fixé par `KC_HOSTNAME` dans `docker-compose.yml`. Depuis un conteneur, la découverte (`http://keycloak:8080/realms/dlnuf/.well-known/openid-configuration`) renvoie l'émetteur public et des points d'accès serveur à serveur internes.

## Modifier le realm

Keycloak n'importe le realm que s'il n'existe pas encore. Après une modification de `import/realm-dlnuf.json` :

```bash
sh infrastructure/keycloak/reimport.sh
```

Le script supprime le realm puis redémarre Keycloak, qui le réimporte. Les réglages faits à la main dans la console sont perdus : il faut reporter toute modification durable dans le fichier JSON.

## Limites connues (prototype)

- Secrets et PIN de démonstration écrits en clair dans le fichier du realm : valeurs de développement uniquement.
- Pas de second facteur ni de réinitialisation du PIN par SMS : à ajouter si le temps le permet.
- `start-dev` : HTTP sans TLS, configuration de développement.
