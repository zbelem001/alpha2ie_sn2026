# Catalogue métier des six administrations

Les modèles ci-dessous sont des parcours de démonstration à valider avec les
administrations, pas une liste officielle et exhaustive de pièces ou de conditions.
Leur pré-vérification ne décide pas de la délivrance d'un titre.

| Administration | Démarches configurées |
| --- | --- |
| État civil | Copie d'acte de naissance ; préparation d'une rectification d'acte |
| Justice | Certificat de nationalité ; bulletin de casier judiciaire |
| Trésor | Vérification de paiement ; duplicata de reçu |
| ONI | Pré-vérification CNIB ; correction d'état civil sur une CNIB |
| Police des frontières | Passeport ordinaire ; renouvellement de passeport |
| Fonction publique | Candidature à un concours ; prise de service |

Les douze démarches sont publiées et actives depuis le 18 novembre 2026 : deux
par administration, visibles dans le portail citoyen et le guichet de leur
administration. Les services utilisés et leurs droits X-Road ont été synchronisés.
La publication explicite peut être relancée avec `python -m scripts.publish_administration_catalog`.
L’initialisation ordinaire conserve les choix ultérieurs de publication ou de désactivation.

| Administration | Services API disponibles | Services déclarés à raccorder (désactivés) |
| --- | --- | --- |
| État civil | Retrouver un acte ; vérifier la majorité | — |
| Justice | Nationalité ; indicateur de casier ; validité d'un bulletin | — |
| Trésor | Vérifier un paiement | Authenticité d'un reçu |
| ONI | Validité d'une CNIB | Disponibilité d'une carte pour retrait |
| Police des frontières | — | Validité d'un passeport ; déclaration de perte de passeport |
| Fonction publique | — | Statut actif d'un agent public ; admission à un concours |

Les sept services disponibles ont une API REST existante. Leur présence au catalogue
ne démontre pas une publication ni une autorisation X-Road. Les six autres restent
désactivés jusqu'à l'implémentation et au raccordement de leur API et de leurs données.
Une perte de passeport n'est pas assimilée au registre optionnel des pertes de CNIB.

Chaque démarche lie des vérifications à leurs services fournisseurs, avec une clé
booléenne attendue et le type de référence documentaire à demander au traitement du
dossier. Les références de paiement restent transactionnelles ; aucun identifiant
universel de citoyen n'est ajouté au profil.

Stockage : base métier `backend`, tables `registry_services`, `procedures`,
`questions`, `procedure_questions` et `registries`. Les données des citoyens restent
dans les bases des registres. L'initialisation `scripts.seed_administration_catalog`
est transactionnelle et idempotente : elle ajoute les éléments absents et conserve
les modifications et désactivations existantes.
