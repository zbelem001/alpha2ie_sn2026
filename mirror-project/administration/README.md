# Console administrateur

Application indépendante sur **http://localhost:3002**, issue de l’interface admin de `main` et reliée aux API du miroir.

Depuis ce dossier : `npm ci`, puis `npm run dev`. Avec Docker, depuis `mirror-project/` :

```sh
docker compose up -d --build administration
```

La connexion utilise le numéro et le PIN d’un compte Keycloak portant le rôle `local-admin` et un `administration_code` valide. Aucun compte n’est créé depuis cette interface. Ses cookies de session sont distincts de ceux des autres espaces.

Menu : vue d’ensemble, dossiers, démarches, droits d’échange, registre et services, agents, historique. Les dossiers réutilisent le module du guichet. Les données proviennent du serveur ; le test de registre reste explicitement simulé. Voir [la documentation de la console](../docs/console-administration.md).

Ports des applications : citoyen **3000**, agent **3001**, administrateur **3002**.
