# Administrations : fournir et demander des informations

Une administration n'a pas de rôle fixe « fournisseur » ou « demandeur ».
Elle possède des services et des démarches. Dans chaque échange, le service
identifie le fournisseur et la démarche identifie l'administration demandeuse.
Les rôles des utilisateurs restent distincts : administrateur local, agent,
citoyen et administrateur technique X-Road.

## Configuration commune

`passerelle/connectors/administrations.json` décrit les six administrations :
code métier, membre et sous-système X-Road, serveur d'hébergement et URL du
registre lorsqu'elle existe. Aucun indicateur ne restreint une administration
à fournir ou à demander. Les propriétés `services` et `allowed` décrivent
uniquement les services et conventions initiaux du banc, pas des capacités fixes.

Les noms Docker `ss-registres` et `ss-demandeurs` sont conservés pour préserver
les certificats, volumes et enregistrements. Chaque serveur peut héberger des
sous-systèmes qui fournissent et consomment des services.

Le script de configuration X-Road et la synchronisation métier lisent le même
catalogue. Publication, activation et droits sont appliqués au serveur qui
héberge le fournisseur. Une administration inconnue produit une erreur explicite.

## Parcours

1. Chaque administration retrouve Démarches et Registre et services dans sa console.
2. Elle peut enregistrer son URL d'API et tester réellement `/health`.
3. Elle déclare un service REST existant avec sa clé de réponse booléenne.
   Une vérification est créée pour rendre ce service sélectionnable dans les démarches.
4. Une démarche choisit des vérifications locales ou distantes, leur ordre,
   les références documentaires et les règles métier.
5. La publication utilise les mécanismes de droits et de synchronisation existants.
6. L'exécution prend l'identité et le serveur X-Road de l'administration propriétaire
   du dossier. Le mode direct utilise aussi les URL de registres enregistrées en base.

Les droits restent accordés par service ; cette correction n'accorde pas d'accès
général entre toutes les administrations. Le consentement et la traçabilité restent
nécessaires selon le parcours. Une déclaration ne génère pas une API ou une base.
La Fonction publique et la Police des frontières n'ont actuellement pas d'API
fournisseur dédiée : leur capacité à déclarer des services est ouverte, mais il
faut implémenter et raccorder leur API avant de publier un véritable service.

## Configuration locale des serveurs

Le backend accepte les variables `XROAD_ADMIN_URL_SS_REGISTRES`,
`XROAD_ADMIN_URL_SS_DEMANDEURS`, `XROAD_SECURITY_SERVER_URL_SS_REGISTRES` et
`XROAD_SECURITY_SERVER_URL_SS_DEMANDEURS`. Elles permettent de changer les adresses
sans changer l'identité des administrations. Le compte technique du banc reste
celui configuré par `XROAD_ADMIN_USER` et `XROAD_ADMIN_PASSWORD`.

Référence : [guide des Security Servers X-Road](https://docs.x-road.global/Manuals/ug-ss_x-road_6_security_server_user_guide.html).
