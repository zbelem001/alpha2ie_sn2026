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
| `keycloak` | Identités, sessions, rôles : realm `dlnuf` importé au démarrage ([keycloak/README.md](keycloak/README.md)) | 8180 |
| `civil-registry`, `transport-registry` | Registres simulés | 8101, 8102 |
| `justice-registry`, `police-registry`, `treasury-registry` | Registres fictifs | 8103, 8104, 8105 |

Les ports 5432 et 8080 ne sont pas utilisés côté machine, car ils sont souvent déjà occupés.

Mémoire : environ 0,85 Go au total, dont environ 565 Mo pour Keycloak.

## Simuler une panne

```bash
docker compose stop justice-registry
docker compose start justice-registry
```

Pendant la panne, le connecteur répond `unavailable` ; il n'invente jamais de réponse.

## À venir

- Notifications simulées (SMS et e-mail).
- Services `backend` et `frontend`, déjà préparés en commentaire dans `docker-compose.yml`.
