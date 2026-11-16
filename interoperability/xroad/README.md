# X-Road (phase 3)

À faire une fois les registres et les connecteurs stables. Le banc de test suit l'environnement Docker Compose documenté par le NIIS.

| Conteneur | Rôle | Membre servi |
|---|---|---|
| `cs` | Serveur central | — |
| `ca` | Autorité de certification de test, OCSP, horodatage | — |
| `ss1` | Serveur de sécurité de gestion | — |
| `ss2` | Serveur de sécurité client | `BF/GOV/ONI` (sous-système `CNIB`) |
| `ss3` | Serveur de sécurité fournisseur | Mairie, Transports, Justice, Police, Trésor |

Services REST à déclarer sur `ss3` : chaque `POST /services/{service}` des registres (voir `../README.md`). Droits d'accès : `BF/GOV/ONI/CNIB` uniquement vers les services prévus par les conventions.

Points d'attention :

- La configuration initiale se fait en grande partie à la main. Chaque étape doit être notée ici, sous forme de script ou de procédure.
- La machine de développement a 10 Go de RAM. Il faut vérifier tôt que les cinq conteneurs tiennent en même temps que le reste.
- Plan de repli : si X-Road n'est pas prêt, `REGISTRY_CONNECTOR=direct` garde tout fonctionnel.
