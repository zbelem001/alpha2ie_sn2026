# Démarrage local simplifié

Depuis `mirror-project`, après installation de Docker Desktop :

```powershell
# Première construction ou changement du code
.\scripts\start-local.ps1 -Build -XRoad

# Démarrages suivants avec les échanges X-Road
.\scripts\start-local.ps1 -XRoad
```

Le script supprime uniquement les conteneurs d'initialisation qui se sont arrêtés
avec succès. Les volumes de données, certificats et configurations sont conservés.
Une initialisation encore en cours ou en erreur reste visible pour diagnostic.

## Ce qui tourne

| Fonction | Conteneur |
| --- | --- |
| Bases de données | `dlnuf-base-donnees` |
| Connexion et comptes | `dlnuf-identite` |
| Registres actifs | `dlnuf-registre-etat-civil`, `dlnuf-registre-justice`, `dlnuf-registre-tresor`, `dlnuf-registre-cnib` |
| API métier | `dlnuf-api-demarches` |
| Notifications simulées | `dlnuf-notifications` |
| Interfaces | `dlnuf-portail-citoyen`, `dlnuf-guichet-agent`, `dlnuf-console-administration` |

Soit 11 conteneurs applicatifs permanents. CNIB reste présent car la démarche
passeport l'utilise. Les trois bases PostgreSQL des registres partagent un seul
conteneur PostgreSQL, avec des bases et des comptes distincts.

Le profil `xroad` ajoute quatre conteneurs permanents : serveur central,
autorité de certification de test et deux Security Servers. Le programme
`xroad-setup` configure le banc puis s'arrête. Ces composants sont nécessaires au
banc X-Road actuel. Les noms historiques des deux serveurs ne limitent pas les
administrations à un rôle fournisseur ou demandeur.

Transport et déclarations de perte sont optionnels :

```powershell
.\scripts\start-local.ps1 -XRoad -Extended -Build
```

Pour travailler uniquement sur les interfaces, sans démarrer X-Road :

```powershell
.\scripts\start-local.ps1
```

Les composants X-Road déjà en cours ne sont pas arrêtés par cette commande.
Sans X-Road, les consultations exigent `REGISTRY_CONNECTOR=direct`, et les
modifications métier ne peuvent pas synchroniser des droits X-Road si
`XROAD_SYNC_ENABLED=true`. Ce mode sert au développement des interfaces,
pas à démontrer les échanges sécurisés.

Les images construites ont des étiquettes `dlnuf/...:local` lisibles. Une empreinte
`sha256:...` reste un identifiant interne Docker ; aucune suppression globale
d'images ou de volumes n'est nécessaire pour rendre la liste lisible.
