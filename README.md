# Dites-le-nous une fois

Hackathon des universités 2026 · Finale · Sujet 02.

Socle d’interopérabilité administrative : vérifications ciblées, consentement, traçabilité et reprise après indisponibilité d’un registre. Les administrations obtiennent directement auprès des registres officiels les informations nécessaires à une démarche, au lieu de demander des pièces à l’usager.

## État du dépôt

| Lot | État |
|---|---|
| `interoperability/`, `infrastructure/` | Registres simulés, connecteurs, notifications simulées et Docker Compose opérationnels (voir « Démarrer ») ; banc X-Road facultatif, validé de bout en bout ([interoperability/xroad](interoperability/xroad/README.md)) |
| `contracts/` | Contrats proposés, à valider : backend ↔ registres (`registry-request`, `registry-response`) et backend ↔ notifications (`notification-request`, `notification-response`, `sms-reply`) ; autres schémas réservés |
| `frontend/` | À initialiser par la Personne 1 |
| `backend/` | API FastAPI, base PostgreSQL, Keycloak et catalogue de démonstration intégrés dans Compose |

Les fichiers `.gitkeep` permettent à Git de conserver les dossiers réservés.

## Responsabilités

| Dossier | Responsable | Contenu |
|---|---|---|
| `frontend/` | Personne 1 | Interfaces citoyenne et administrative, Next.js / TypeScript |
| `backend/` | Personne 2 | API FastAPI, consentements, orchestration, autorisations, audit |
| `interoperability/` | Personne 3 | X-Road, adaptateurs, registres et notifications simulés |
| `infrastructure/` | Personne 3 | Docker Compose, Keycloak et PostgreSQL |
| `contracts/` | Collectif | OpenAPI, schémas JSON et exemples partagés |
| `docs/` | Collectif | Architecture, API, modèle de données et installation |

Le catalogue de démonstration contient deux parcours : la **pré-vérification partielle d’une candidature à un concours direct** et la **pré-vérification d’une demande de passeport ordinaire**. Leurs contrôles et limites sont détaillés dans la [documentation de l’API](docs/api-documentation.md).

## Démarrer

```bash
docker compose up -d --build
```

| Service | Adresse sur la machine |
|---|---|
| Registre d’état civil | http://localhost:8101/docs |
| Registre des transports | http://localhost:8102/docs |
| Justice (nationalité, casier) | http://localhost:8103/docs |
| Police (pertes) | http://localhost:8104/docs |
| Trésor (paiements, simulé) | http://localhost:8105/docs |
| ONI (statut CNIB simulé) | http://localhost:8106/docs |
| Notifications simulées : boîte d'envoi, téléphone du citoyen (`/phone/22670000001`) | http://localhost:8107 |
| Keycloak | http://localhost:8180 |
| API métier FastAPI | http://localhost:8000/docs |
| PostgreSQL | localhost:55432 |

Le conteneur backend applique les migrations et charge le catalogue de démonstration au démarrage. Les comptes locaux d’essai sont décrits dans [la documentation API](docs/api-documentation.md).

Pour changer les valeurs par défaut : `cp .env.example .env`, puis modifier `.env`.

Banc X-Road (facultatif, 5,3 Go de mémoire en plus) : `docker compose --profile xroad up -d --build` démarre et configure tout, en une commande (prêt après 12 à 16 minutes la première fois). Pour l'activer par défaut : `COMPOSE_PROFILES=xroad` dans `.env`. Détails : [interoperability/xroad/README.md](interoperability/xroad/README.md).

### SMS et codes Infobip

Deux clés API distinctes sont attendues dans le `.env` local : `INFOBIP_OTP_API_KEY` pour les OTP d’inscription et de consentement, et `INFOBIP_SMS_API_KEY` pour les SMS simples. Elles peuvent être créées avec des droits API différents. Le domaine du compte (`INFOBIP_BASE_URL`), `TEST_PHONE_NUMBER` et l’expéditeur SMS (`INFOBIP_SENDER`) complètent la configuration. `.env` est ignoré par Git ; `.env.example` ne contient que des valeurs vides pour les secrets.

Pour la 2FA, créer une application Infobip avec un PIN à six chiffres, cinq essais et une durée de vie de cinq minutes. Créer dans cette application deux modèles SMS qui contiennent `{{pin}}` : un pour l’inscription et un pour le consentement. Reporter l’identifiant de l’application dans `INFOBIP_2FA_APPLICATION_ID` et les deux identifiants de modèles dans `INFOBIP_2FA_REGISTRATION_MESSAGE_ID` et `INFOBIP_2FA_CONSENT_MESSAGE_ID`. Infobip génère le PIN, l’envoie et le valide avec son identifiant `pinId`; le backend ne fabrique ni ne stocke le code. Infobip décrit ce flux dans sa [documentation officielle 2FA](https://www.infobip.com/docs/2fa-service/using-2fa-api).

En essai, les routes OTP et les SMS simples n’envoient qu’à `TEST_PHONE_NUMBER`. Le destinataire demandé doit donc être ce numéro vérifié, sinon le backend refuse l’envoi. Les SMS simples utilisent l’API v3 `POST /sms/3/messages` et le champ `sender`; voir le [guide officiel Infobip SMS](https://www.infobip.com/docs/tutorials/send-your-first-sms-message-using-infobip-api).

Depuis `backend/`, charger la configuration puis prévisualiser un SMS simple sans appel réseau :

Depuis `backend/`, charger la configuration puis prévisualiser le message personnalisé sans appel réseau :

```bash
set -a
. ../.env
set +a
python -m scripts.test_infobip_sms --dry-run
```

Après avoir vérifié le numéro de test, envoyer un seul SMS :

```bash
python -m scripts.test_infobip_sms
```

Le texte des SMS simples est modifiable dans `backend/app/sms_templates.py`. Le script affiche l’identifiant `messageId` et le statut Infobip ; un statut accepté indique une prise en charge par l’API, pas nécessairement la livraison finale. Il avertit si le texte dépasse 160 caractères ou utilise Unicode (segments de 70 caractères).

Pour un consentement à distance, l’ouverture du dossier crée aussi une notification plateforme et envoie le SMS d’invitation simple. Pour un recueil assisté au guichet, l’agent demande un OTP Infobip par `POST /v1/cases/{case_id}/consent/otp`, puis vérifie le PIN communiqué par le citoyen avec `POST /v1/cases/{case_id}/consent/otp/verify`. Le code est géré par Infobip; le backend conserve uniquement `pinId` et le périmètre de consentement. Les envois restent limités à cinq par dossier et par heure, avec 30 secondes entre les renvois.

Pour l’inscription, `POST /v1/auth/registration/otp` envoie le code et `POST /v1/auth/registration/otp/verify` le vérifie. Ces routes sont prêtes côté backend, mais l’écran frontend utilise encore une simulation locale. La création effective du compte Keycloak après vérification reste à raccorder.

## Contrat entre le backend et les registres

Le backend interroge un registre par :

```python
connector.query(organization="BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL", service="identity", payload={...})
```

- Requête (`payload`) : [contracts/schemas/registry-request.json](contracts/schemas/registry-request.json)
- Réponse : [contracts/schemas/registry-response.json](contracts/schemas/registry-response.json)
- Exemples : [contracts/examples/registry-exchanges.json](contracts/examples/registry-exchanges.json)

Statuts : `ok`, `not_found`, `ambiguous`, `refused`, `unavailable`, `invalid_request`. Seul `ok` porte des données. Le connecteur se choisit par `REGISTRY_CONNECTOR` (`direct`, puis `xroad`), sans modifier l’orchestrateur. Détails dans [interoperability/README.md](interoperability/README.md).

## Règles de travail

- Une branche par tâche, fusion dans `main` par Pull Request.
- Tout changement dans `contracts/` se décide ensemble.
- Chaque lot se teste seul, avec des mocks conformes aux contrats.
- X-Road ne doit pas bloquer le développement des interfaces ou du cœur métier.

## Documentation

- [Architecture et organisation](docs/architecture.md) : document de référence en cas de contradiction
- [Guide du projet](DITES-LE-NOUS-UNE-FOIS.md)
- [Interfaces prévues](interfaces%283%29.md)
- [Architecture avec X-Road](docs/architecture-xroad.md.pdf)
- [Variante : socle sans X-Road](docs/architecture-socle.md)
- [Contrats API](docs/api-documentation.md)
- [Modèle de données](docs/database-schema.md)
- [Guide d’ajout d’une démarche](docs/guide-ajout-demarche.md)
- [Installation](docs/installation.md)

## Licence

À choisir collectivement. `LICENSE` est un emplacement réservé et n’accorde pas de licence libre à ce stade.
