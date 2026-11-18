# Branchements

Registres d'autres équipes branchés sur notre passerelle, pile démarrée, sans reconstruction ni redémarrage.

Chaque fichier `*.json` (écrit par `passerelle/brancher.py`) ou `*.yaml` est relu à chaque appel :

- par la garde de la couche consentement-minimisation (`HOLDERS_OVERRIDES`) : clé `holders`, qui remplace l'adresse d'un registre (ses règles restent celles de `holders.yaml`) ou ajoute un détenteur avec ses règles ;
- par le connecteur direct de la couche démarches (`REGISTRY_ROUTES_OVERRIDES`) : clé `routes`, pour joindre un nouveau détenteur par la garde.

Les fichiers écrits par l'outil (`*.json`) ne sont pas versionnés : ils décrivent un branchement en cours, pas la configuration du projet. Mode d'emploi : [passerelle/README.md](../../passerelle/README.md#brancher-le-registre-dune-autre-équipe).
