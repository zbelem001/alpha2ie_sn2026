# Infrastructure du miroir

Responsable : Personne 3. Copie de `infrastructure/` (branche `main`), adaptée aux dossiers de couche du miroir.

```bash
# depuis mirror-project/
docker compose up -d --build
docker compose ps
```

`mirror-project/compose.yaml` inclut `infrastructure/docker-compose.yml` et le banc X-Road de la passerelle. `.env.example` contient une configuration locale de démonstration complète. Pour un environnement partagé, copier ce fichier en `.env` puis remplacer les mots de passe et secrets.

| Service | Rôle | Port sur la machine |
|---|---|---|
| `postgres` | Bases `keycloak` et `backend` (créées par `postgres/init/`) | 55432 |
| `keycloak` | Identités, sessions, rôles | 8180 |
| `keycloak-profile-init` | Initialise les attributs des comptes de démonstration après l’import du realm | aucun (tâche ponctuelle) |
| `civil-registry`, `transport-registry` | Registres simulés | 8101, 8102 |
| `justice-registry`, `police-registry`, `treasury-registry`, `oni-registry` | Registres fictifs | 8103, 8104, 8105, 8106 |
| `notifications` | SMS et e-mails simulés : boîte d'envoi et téléphone du citoyen ([passerelle/README.md](../passerelle/README.md)) | 8107 |
| `demarches` | API métier (couche démarches, copie du backend) | 8000 |
| `espace-usager` | Interface du citoyen (Next.js), branchée sur Keycloak et l'API démarches | 3000 |
| `guichet-agent` | Interface de l'agent (Next.js), branchée sur Keycloak et l'API démarches | 3001 |

Les ports 5432 et 8080 ne sont pas utilisés côté machine, car ils sont souvent déjà occupés.

`keycloak-profile-init` est une tâche idempotente exécutée avant la couche démarches. Elle déclare les claims `administration_code`, `citizen_ref`, `phone_number` et `phone_number_verified` dans le profil Keycloak, puis les associe aux comptes fictifs. En démonstration, le numéro Infobip configuré dans `TEST_PHONE_NUMBER` est transmis via `CITIZEN_DEMO_PHONE`. Le claim vérifié reste `false` par défaut ; ne définir `CITIZEN_DEMO_PHONE_VERIFIED=true` qu’après avoir confirmé la possession du numéro par un canal indépendant. La référence `citizen_ref` est rattachée ensuite par `POST /v1/citizen/identity-link`. La version du realm utilisée ne permet pas de déclarer ces attributs directement dans son fichier d’import.

Mémoire : environ 0,85 Go au total, dont environ 565 Mo pour Keycloak.

## Banc X-Road (facultatif)

```bash
docker compose --profile xroad up -d --build        # démarre et configure le banc
docker compose --profile xroad logs -f xroad-setup  # suivre la configuration
```

Serveur central, autorité de test et deux Security Servers, définis dans `../passerelle/xroad/docker-compose.xroad.yml`. Le service `xroad-setup` configure le banc tout seul puis s'arrête. Environ 5,3 Go de mémoire en plus ; prêt après 12 à 16 minutes la première fois. Pour activer le banc par défaut : `COMPOSE_PROFILES=xroad` dans `.env`. Détails : [passerelle/xroad/README.md](../passerelle/xroad/README.md).

## Simuler une panne

```bash
docker compose stop justice-registry
docker compose start justice-registry
```

Pendant la panne, le connecteur répond `unavailable` ; il n'invente jamais de réponse. De même, `docker compose stop notifications` fait répondre `unavailable` au client de notifications.

## À venir

- Rien pour l'instant : toutes les couches du miroir démarrent avec `docker compose up -d --build`.
