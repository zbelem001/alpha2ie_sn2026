# Trois bases administratives et 100 citoyens fictifs

| Administration | Base PostgreSQL | Compte technique |
|---|---|---|
| État civil | `registry_civil` | `registry_civil_owner` |
| Justice | `registry_justice` | `registry_justice_owner` |
| Trésor | `registry_treasury` | `registry_treasury_owner` |

Les bases sont séparées dans le serveur PostgreSQL local existant. Les comptes des registres ne sont ni superutilisateurs ni créateurs de bases ou de rôles. La connexion publique aux trois bases est retirée : le compte d’un registre ne peut pas se connecter à la base d’un autre. Le compte de provisionnement conserve les privilèges nécessaires à leur initialisation.

Le service `registry-db-init` crée les bases, les comptes et la table `registry_records` (clé locale, données JSONB, date de modification). Les mots de passe sont dans le `.env` local ignoré par Git, transmis uniquement aux services concernés. Pour une nouvelle installation, les valeurs de repli du Compose sont réservées au développement ; définir des secrets privés avant tout usage partagé.

## Jeu fictif

Cent personnes supplémentaires sont générées de façon déterministe par `registres/registries/common/synthetic.py`. Chaque personne a une fiche dans les trois bases : naissance, nationalité/casier et paiement. Les noms `FICTIF_001` à `FICTIF_100` et les références `*-SYNTH-*` indiquent clairement la simulation. Il existe des mineurs, des personnes non burkinabè, des casiers avec condamnation, des bulletins non valides et des paiements en attente.

Les anciennes fixtures sont conservées afin de ne pas casser les scénarios déjà utilisés. Il y a donc **100 nouvelles fiches par base**, en plus des fixtures existantes. Le marqueur `_seed_batch = synthetic-100-v1` permet de les compter séparément. Aucun compte citoyen Keycloak n’est créé et aucun SMS n’est envoyé.

Les références sont propres aux registres : `ACTE-SYNTH-0001`, `NAT-SYNTH-0001`, `CASIER-SYNTH-0001`, `PAY-SYNTH-0001`. Le champ `pivot_id` est uniquement une compatibilité interne aux scénarios actuels ; il ne constitue pas un identifiant officiel universel.

## Démarrer ou relancer

Depuis `mirror-project/` :

```sh
docker compose up -d --build civil-registry justice-registry treasury-registry
docker compose logs registry-db-init
```

L’initialisation utilise `ON CONFLICT DO NOTHING` : une relance n’ajoute pas de doublons et n’écrase pas les données existantes. Les bases persistent dans le volume PostgreSQL existant. Ne pas supprimer ce volume pour réinitialiser les registres : il contient également Keycloak et le backend.

## API et flux

Les URL et contrats des registres restent les mêmes : ports 8101, 8103 et 8105, routes `/services/{service}`. Lorsqu’une URL de base de données est configurée, les requêtes lisent PostgreSQL, sans cache du fichier JSON. La santé du service vérifie aussi l’accès à sa base. Une panne de base ne bascule pas silencieusement sur les fixtures.

Les paiements créés ou confirmés par les routes de simulation du Trésor sont également enregistrés en base. Sans `REGISTRY_DATABASE_URL`, les tests et les registres non migrés peuvent continuer à utiliser leurs fichiers JSON.

X-Road conserve les mêmes adresses de services. Migrer le stockage ne bascule pas le backend métier du mode `direct` au mode `xroad`. Cela ne change pas non plus les règles de consentement ni les champs actuellement exposés par chaque service ; la minimisation complète reste à finaliser comme indiqué dans l’audit.
