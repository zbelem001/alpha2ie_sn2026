# Dites-le-nous une fois — branche `mirror-project`

Hackathon des universités 2026 · Finale · Sujet 02.

Cette branche ne contient que l'**architecture par couche** : tout est dans [mirror-project/](mirror-project/README.md), qui se lance, se teste et se documente seul (`docker compose up -d --build` depuis `mirror-project/`).

L'organisation d'origine (`frontend/`, `backend/`, `interoperability/`, `contracts/`, `infrastructure/`, `docs/`) est sur la branche `main`, inchangée. Elle n'est plus présente ici, pour ne pas avoir chaque fichier en double. Si le miroir est validé, son contenu remplacera cette organisation sur `main`.

Restent à la racine : ce fichier, `.gitignore` (règles valables pour tout le dépôt, dont la protection des secrets) et `LICENSE` (emplacement réservé, licence à choisir collectivement).
