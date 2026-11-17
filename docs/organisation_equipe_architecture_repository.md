# Dites-le-nous une fois

## Organisation de l'équipe et architecture du repository

Le projet est développé par une équipe de trois personnes. L'objectif est de répartir les responsabilités clairement et de permettre à chaque personne d'avancer indépendamment, sans attendre que les autres terminent leurs tâches.

## 1. Répartition des responsabilités

### Personne 1 — Frontend

**Responsabilité :** interfaces citoyenne et administrative.

- Développer le portail citoyen.
- Développer le tableau de bord administratif.
- Concevoir les interfaces des démarches et les formulaires.
- Concevoir le parcours de consentement.
- Afficher l'historique des consultations.
- Intégrer les API du backend.

**Livrable :** interfaces fonctionnelles, testables avec des données simulées (mocks), même si le backend n'est pas encore terminé.

### Personne 2 — Backend métier

**Responsabilité :** logique métier et traitement des demandes.

- Développer le catalogue des démarches.
- Gérer les consentements et leur révocation.
- Gérer les demandes administratives et leurs états.
- Développer l'orchestration des requêtes.
- Gérer les autorisations et les contrôles métier.
- Enregistrer les consultations et l'historique.
- Intégrer les connecteurs aux registres via une interface commune.

**Livrable :** API métier documentée et testée, utilisant un connecteur simulé en attendant l'intégration réelle avec X-Road.

### Personne 3 — Interopérabilité et infrastructure

**Responsabilité :** échanges entre administrations et environnement technique.

- Installer et configurer X-Road.
- Développer les connecteurs vers les services administratifs.
- Créer des API de simulation pour les registres (état civil, transport, etc.).
- Configurer les échanges avec les Security Servers X-Road.
- Préparer Docker Compose et l'environnement de développement.
- Tester les échanges interadministratifs.
- Préparer les notifications simulées (SMS ou e-mail).

**Livrable :** environnement d'interopérabilité testable avec des registres fictifs, puis connecté à X-Road.

## 2. Architecture du repository

Le projet utilise un **monorepo Git** : un seul dépôt, avec des dossiers séparés par responsabilité.

```text
dites-le-nous-une-fois/
│
├── frontend/                              # PERSONNE 1
│   ├── app/
│   │   ├── (citizen)/                     # Espace citoyen
│   │   ├── (administration)/               # Espace administration
│   │   └── (auth)/                         # Pages de connexion
│   ├── components/                        # Composants UI réutilisables
│   ├── services/                          # Clients et appels API
│   ├── hooks/                             # Hooks React
│   ├── types/                             # Types TypeScript
│   ├── mocks/                             # Données et réponses simulées
│   └── package.json
│
├── backend/                               # PERSONNE 2
│   ├── app/
│   │   ├── modules/
│   │   │   ├── procedures/                # Catalogue des démarches
│   │   │   ├── consent/                   # Consentements
│   │   │   ├── requests/                  # Demandes administratives
│   │   │   ├── orchestration/             # Coordination des requêtes
│   │   │   ├── audit/                     # Traçabilité et historique
│   │   │   └── users/                     # Utilisateurs et rôles métier
│   │   ├── connectors/
│   │   │   ├── interfaces/                # Contrats des connecteurs
│   │   │   └── mock/                      # Connecteur simulé
│   │   ├── core/                          # Configuration et dépendances
│   │   ├── database/                      # Accès aux données
│   │   └── main.py                        # Point d'entrée FastAPI
│   ├── tests/
│   └── requirements.txt
│
├── interoperability/                      # PERSONNE 3
│   ├── xroad/
│   │   ├── configuration/                # Configuration X-Road
│   │   └── services/                      # Services exposés via X-Road
│   ├── connectors/                        # Adaptateurs vers les registres
│   ├── registries/
│   │   ├── civil_registry/                # Registre d'état civil simulé
│   │   └── transport_registry/            # Registre des transports simulé
│   ├── mock_registry/                     # Autres services fictifs
│   └── tests/
│
├── contracts/                             # COLLECTIF
│   ├── openapi/
│   │   └── backend.yaml                   # Contrat API du backend
│   ├── schemas/
│   │   ├── citizen.json
│   │   ├── consent.json
│   │   ├── request.json
│   │   └── registry-response.json
│   └── examples/                          # Exemples de requêtes et réponses
│
├── infrastructure/                        # PERSONNE 3
│   ├── docker/
│   ├── keycloak/                          # Configuration Keycloak
│   ├── postgres/                          # Initialisation PostgreSQL
│   └── docker-compose.yml
│
├── docs/                                  # COLLECTIF
│   ├── architecture.md
│   ├── api-documentation.md
│   ├── database-schema.md
│   └── installation.md
│
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

## 3. Attribution des dossiers

| Dossier | Responsable | Périmètre |
|---|---|---|
| `frontend/` | Personne 1 | Portails citoyen et administratif |
| `backend/` | Personne 2 | API et logique métier |
| `interoperability/` | Personne 3 | X-Road, connecteurs et registres simulés |
| `infrastructure/` | Personne 3 | Docker, environnement et configuration technique |
| `contracts/` | Collectif | Contrats API et schémas de données |
| `docs/` | Collectif | Documentation du projet |

## 4. Règles de travail pour éviter les blocages

### 4.1 Définir les contrats avant le développement

Les trois personnes définissent ensemble les endpoints, les formats JSON, les paramètres, les codes d'erreur et les schémas de données. Ces contrats sont documentés dans `contracts/` et ne sont modifiés qu'après accord des personnes concernées.

### 4.2 Utiliser des composants simulés (mocks)

Chaque personne doit pouvoir développer et tester sans attendre les autres :

- **Frontend :** utilise des réponses JSON simulées conformes au contrat OpenAPI.
- **Backend :** utilise un `MockRegistryConnector` qui renvoie des réponses prédéfinies.
- **Interopérabilité :** teste les connecteurs avec des registres fictifs, indépendamment de l'orchestrateur métier.

### 4.3 Séparer les responsabilités dans Git

- Une branche par fonctionnalité ou tâche.
- Chaque personne travaille principalement dans les dossiers qui lui sont attribués.
- Les changements dans `contracts/` sont coordonnés collectivement.
- Les modifications passent par des Pull Requests avant leur fusion dans `main`.
- Les conflits ou changements transversaux sont discutés avant intégration.

### 4.4 Exiger des tests indépendants

Chaque lot doit pouvoir être lancé et testé séparément avec ses propres données de test. Les tests d'intégration entre les trois lots sont ajoutés progressivement, sans rendre le développement individuel dépendant de leur disponibilité.

## 5. Communication entre les trois lots

```text
PERSONNE 1 — FRONTEND
        │
        │ Contrats OpenAPI + réponses simulées
        ▼
PERSONNE 2 — BACKEND MÉTIER
        │
        │ Interface de connecteur + connecteur simulé
        ▼
PERSONNE 3 — INTEROPÉRABILITÉ
        │
        │ Registres fictifs puis services X-Road
        ▼
ADMINISTRATIONS / REGISTRES
```

Le frontend ne dépend pas de la disponibilité du backend réel. Le backend ne dépend pas de la disponibilité de X-Road. Les intégrations réelles remplacent les mocks lorsque les composants correspondants sont prêts.

### 5.1 Exemple de connecteur interchangeable

Le backend utilise un contrat abstrait pour interroger un registre :

```python
from typing import Protocol, Any

class RegistryConnector(Protocol):
    def query(
        self,
        organization: str,
        service: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ...
```

Deux implémentations respectent ce même contrat :

```text
RegistryConnector
       ├── MockRegistryConnector  → réponses fictives
       └── XRoadConnector         → appels via X-Road
```

La personne 2 peut donc développer l'orchestration avec le connecteur simulé. La personne 3 développe séparément l'implémentation X-Road. Le remplacement du mock par le connecteur réel ne doit pas nécessiter de réécrire l'orchestrateur.

## 6. Stack technologique

| Couche | Technologie | Utilisation |
|---|---|---|
| Frontend | **Next.js, React, Tailwind CSS** | Portails citoyen et administratif |
| Langage frontend | **TypeScript** | Typage et fiabilité du frontend |
| Backend | **Python, FastAPI, Pydantic** | API REST et logique métier |
| Base de données | **PostgreSQL** | Citoyens, démarches, consentements, demandes et historique |
| Authentification | **Keycloak** | Gestion des identités, sessions et rôles |
| Interopérabilité | **X-Road** | Échanges sécurisés entre administrations |
| Conteneurisation | **Docker, Docker Compose** | Environnement reproductible et lancement local |
| Contrats API | **OpenAPI, Swagger UI** | Documentation et partage des interfaces |
| Tests backend | **Pytest** | Tests unitaires et d'intégration |
| Gestion de versions | **Git, GitHub** | Branches, Pull Requests et collaboration |

### Choix volontairement reportés après le MVP

- **Redis :** à ajouter uniquement si un besoin réel de cache ou de tâches asynchrones apparaît.
- **Kafka / RabbitMQ :** non nécessaires pour le premier MVP.
- **Kubernetes :** à éviter au démarrage ; Docker Compose suffit pour l'environnement de démonstration.
- **MongoDB :** PostgreSQL répond aux besoins relationnels du projet et permet aussi de stocker certains champs flexibles avec JSONB.
- **Microservices :** commencer par un backend modulaire unique pour limiter la complexité de déploiement et d'intégration.

## Principe directeur

**Un monorepo modulaire, des contrats partagés et des composants simulés.** Chaque personne possède un périmètre clair, un livrable testable et des interfaces définies. X-Road ne doit pas être un prérequis au développement du frontend ou du cœur métier.
