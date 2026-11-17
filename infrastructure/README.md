# Infrastructure

Responsable : Personne 3.

```bash
# depuis la racine du dépôt
docker compose up -d --build
docker compose ps
```

`compose.yaml`, à la racine, inclut `infrastructure/docker-compose.yml`. Les valeurs par défaut viennent de `.env.example` ; pour les changer, copier ce fichier en `.env`.

| Service | Rôle | Port sur la machine |
|---|---|---|
| `postgres` | Bases `keycloak` et `backend` (créées par `postgres/init/`) | 55432 |
| `keycloak` | Identités, sessions, rôles | 8180 |
| `keycloak-profile-init` | Initialise les attributs des comptes de démonstration après l’import du realm | aucun (tâche ponctuelle) |
| `civil-registry`, `transport-registry` | Registres simulés | 8101, 8102 |
| `justice-registry`, `police-registry`, `treasury-registry`, `oni-registry` | Registres fictifs | 8103, 8104, 8105, 8106 |

Les ports 5432 et 8080 ne sont pas utilisés côté machine, car ils sont souvent déjà occupés.

`keycloak-profile-init` est une tâche idempotente exécutée avant le backend. Elle déclare les claims `administration_code` et `citizen_ref` dans le profil Keycloak, puis les associe aux comptes fictifs. La version du realm utilisée ne permet pas de déclarer ces attributs directement dans son fichier d’import.

Mémoire : environ 0,85 Go au total, dont environ 565 Mo pour Keycloak.

## Simuler une panne

```bash
docker compose stop justice-registry
docker compose start justice-registry
```

Pendant la panne, le connecteur répond `unavailable` ; il n'invente jamais de réponse.

## À venir

- `keycloak/` : realm exporté (rôles `usager`, `agent`, `admin-local`, `admin-centrale`, attributs `identifiant_pivot` et `niveau_garantie`, comptes de démonstration).
- Notifications simulées (SMS et e-mail).
- Services `backend` et `frontend`, déjà préparés en commentaire dans `docker-compose.yml`.
