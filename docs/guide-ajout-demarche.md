# Ajouter une démarche au catalogue

Ce guide décrit l’ajout d’une démarche qui réutilise le modèle actuel du backend. Le catalogue est chargé de façon idempotente par `backend/scripts/seed_demo.py` au démarrage de Compose. Une démarche de catalogue n’ajoute pas, à elle seule, un nouvel endpoint API ni une nouvelle table.

## 1. Décrire le parcours avant de le coder

Pour chaque contrôle, faire valider par l’équipe et l’administration concernée :

- le propriétaire de la démarche et le registre qui détient la réponse ;
- la finalité de chaque consultation, le fondement et les autorisations d’accès ;
- le résultat minimal utile (par exemple « valide : oui/non »), sans rapatrier la pièce ou la fiche complète ;
- les contrôles obligatoires et facultatifs, les règles de reprise après panne et la personne qui traite un résultat incertain ;
- le texte et la version de consentement, sa durée et la conservation du dossier, des preuves et du journal.

Le prototype ne tranche pas les règles administratives ou les durées légales. Il faut les faire confirmer par les responsables compétents avant une démonstration présentée comme conforme.

## 2. Réutiliser ou déclarer les administrations et registres

Dans `ADMINISTRATIONS` de `backend/scripts/seed_demo.py`, ajouter seulement les organismes absents, avec leur code stable. Pour chaque fournisseur de contrôle, le seed crée ou retrouve un registre `main`. Ne pas stocker d’URL, de mot de passe ou de secret dans le catalogue.

Le code d’organisation fournisseur doit correspondre exactement à la clé du routage du connecteur : `interoperability/connectors/routing.yaml` dans Compose et `routing.local.yaml` en exécution locale. Pour un nouveau registre simulé, coordonner son service HTTP et ses données fictives avec la personne 3 ; ne pas détourner l’identifiant d’un autre organisme.

## 3. Définir les questions minimisées

Ajouter chaque contrôle à `QUESTION_DEFINITIONS` sous la forme :

```python
(
    "nouveau_controle",                 # code métier stable et unique
    "BF/GOV/ORGANISME/REGISTRE",         # administration fournisseur
    "service-du-registre",              # POST /services/{service}
    "valid",                            # clé de réponse minimale
    "Vérifier ... sans conserver ...",  # description visible et journalisée
)
```

Le contrat actuel du backend ne sait confirmer automatiquement que les réponses booléennes strictes (`true`/`false`) ou une égalité de `pivot_id` avec la référence du dossier. Une réponse textuelle telle que `"true"`, une date ou un objet est traitée comme invalide. Tout autre type de résultat demande une évolution coordonnée du backend et de `contracts/`, avec tests et règles de minimisation avant de l’utiliser.

La requête envoyée au registre est construite par `backend/app/api.py` : `request_id`, code de démarche et `subject.pivot_id`. Ne pas ajouter de données personnelles au payload sans nécessité démontrée, consentement adapté et mise à jour des contrats.

## 4. Ajouter la démarche et ses permissions

Ajouter une entrée dans `DEMO_PROCEDURES` de `backend/scripts/seed_demo.py` :

```python
{
    "code": "demarche_exemple",
    "config_version": 1,
    "owner": "BF/GOV/ADMIN-DEMANDEUSE",
    "title": "Pré-vérification de ...",
    "questions": [
        ("nouveau_controle", 1, True),
        # ("controle_facultatif", 2, False),
    ],
}
```

Les couples sont `(code_question, position, obligatoire)`. Le seed crée les liens `procedure_questions` et la permission du propriétaire pour chaque contrôle. Le propriétaire doit correspondre à l’administration portée par le jeton agent ; sinon `POST /v1/cases` renvoie `403`.

Un contrôle facultatif ne détermine pas l’état global final, mais il reste proposé au consentement et peut être appelé s’il est autorisé et consenti. Ne le marquez facultatif que si l’équipe comprend et accepte cette règle.

## 5. Vérifier le contrat du registre

Si le service existe déjà, vérifier son nom, son schéma de réponse et le cas fictif choisi dans `interoperability/README.md` et `contracts/examples/registry-exchanges.json`. S’il est nouveau, convenir avec la personne 3 de :

1. la route `POST /services/{service}` et son entrée/sortie minimisées ;
2. l’ajout ou l’extension des schémas et exemples sous `contracts/` ;
3. la fixture fictive nominale et les cas négatif, ambigu ou indisponible pertinents ;
4. l’entrée de routage, le contrôle `/health` et les tests de contrat.

Le statut `ok` doit contenir la clé de réponse attendue. Les statuts autres que `ok` ne doivent pas contenir de données métier. Une indisponibilité donne un contrôle relançable ; le nouvel essai réutilise la vérification logique et ajoute une tentative.

## 6. Démarrer et contrôler le catalogue

Après modification du seed, depuis la racine du dépôt :

```bash
docker compose up -d --build backend
docker compose exec backend python -m scripts.seed_demo
```

Le seed doit pouvoir être exécuté plusieurs fois sans créer de doublons. Pour une modification des tables ou des contraintes, ajouter une migration Alembic revue par l’équipe ; ne pas modifier le schéma à la main ni confondre une modification du catalogue avec une migration.

Avec un jeton d’agent de l’administration propriétaire, contrôler dans Swagger (`http://localhost:8000/docs`) ou avec `curl` :

1. `GET /v1/procedures` expose le nouveau code, titre et liste ordonnée des questions ;
2. `POST /v1/cases` avec ce code crée un dossier et une demande par question ; un jeton d’une autre administration est refusé ;
3. le citoyen correspondant voit les mêmes questions, peut consentir, refuser ou révoquer ; un autre citoyen reçoit `403` ;
4. `POST /v1/cases/{case_id}/checks` ne contacte que les contrôles autorisés et consentis ;
5. `GET /v1/cases/{case_id}` et `/journal` n’exposent que l’état minimal, sans réponse brute ;
6. après simulation d’une panne, la reprise fonctionne et conserve une seule demande logique avec des tentatives distinctes.

Vérifier aussi le parcours nominal, un résultat négatif, une réponse mal formée, un résultat absent et une panne. Documenter les limites métier : `completed` signifie uniquement que les contrôles requis configurés ont abouti, pas que l’administration a pris une décision.

## 7. Corriger ou retirer une démarche

Pour corriger le titre, les questions ou leur caractère obligatoire, modifier la définition et incrémenter `config_version` de la démarche. Le seed applique la version définie à chaque exécution ; ne pas la diminuer. Les dossiers déjà créés ne sont pas automatiquement recalculés : valider avec l’équipe la conduite à tenir pour les dossiers en cours.

Pour retirer une démarche, la désactiver (`active = False`) dans le seed au lieu de supprimer ses lignes. Cela empêche les nouveaux dossiers tout en préservant l’historique. Une question ou un registre déjà utilisé doit aussi être désactivé, pas supprimé.

## Fichiers généralement concernés

- `backend/scripts/seed_demo.py` : administrations, questions, démarche et permissions ;
- `interoperability/connectors/routing.yaml` et `routing.local.yaml` : seulement si un nouveau fournisseur simulé est ajouté ;
- `interoperability/` et `contracts/` : seulement si un service ou contrat change, en coordination avec la personne 3 ;
- `backend/alembic/versions/` : seulement si le modèle de données change ;
- `docs/api-documentation.md` et `interoperability/README.md` : décrire le nouveau parcours, ses données minimales et ses limites.
