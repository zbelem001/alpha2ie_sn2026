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
| `notifications` | SMS et e-mails simulés : boîte d'envoi et téléphone du citoyen ([interoperability/README.md](../interoperability/README.md#notifications-simulées)) | 8106 |

Les ports 5432 et 8080 ne sont pas utilisés côté machine, car ils sont souvent déjà occupés.

Mémoire : environ 0,9 Go au total, dont environ 565 Mo pour Keycloak.

## Banc X-Road (facultatif)

```bash
docker compose --profile xroad up -d --build        # démarre et configure le banc
docker compose --profile xroad logs -f xroad-setup  # suivre la configuration
```

Serveur central, autorité de test et deux Security Servers, définis dans `docker-compose.xroad.yml`. Le service `xroad-setup` configure le banc tout seul puis s'arrête. Environ 5,3 Go de mémoire en plus ; prêt après 12 à 16 minutes la première fois. Pour activer le banc par défaut : `COMPOSE_PROFILES=xroad` dans `.env`. Détails : [interoperability/xroad/README.md](../interoperability/xroad/README.md).

## Simuler une panne

```bash
docker compose stop justice-registry
docker compose start justice-registry
```

Pendant la panne, le connecteur répond `unavailable` ; il n'invente jamais de réponse. De même, `docker compose stop notifications` fait répondre `unavailable` au client de notifications.

## À venir

- Services `backend` et `frontend`, déjà préparés en commentaire dans `docker-compose.yml`.
