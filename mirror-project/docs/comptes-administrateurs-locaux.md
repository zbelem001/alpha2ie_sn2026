# Comptes administrateurs du banc local

Connexion : http://localhost:3002 — PIN commun : `1234`.

| Numéro | Administration |
| --- | --- |
| 10000001 | État civil — Mairie de Ouagadougou |
| 10000002 | Justice |
| 10000003 | Trésor |
| 10000004 | ONI |
| 10000005 | Police des frontières — Passeports |
| 10000006 | Fonction publique |

Chaque compte possède uniquement le rôle métier `local-admin` et le code de
son administration. Les listes de dossiers, démarches, services locaux, agents
et actions sont filtrées par l'administration du jeton. Le catalogue des
services disponibles chez les autres administrations reste visible.

Les anciens administrateurs locaux ont été supprimés lors de la remise à zéro.
Les comptes citoyens, agents et comptes techniques sont conservés.
L'initialisation habituelle crée les comptes manquants et vérifie leur
rattachement, sans réinitialiser leur PIN ni recréer les anciens comptes.

La remise à zéro destructive des seuls administrateurs locaux est explicite :

```powershell
docker compose run --rm --no-deps keycloak-profile-init python -m scripts.local_administrators
```

Ces identifiants simples sont destinés au banc local de démonstration.
