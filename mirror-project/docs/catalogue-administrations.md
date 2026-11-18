# Catalogue initial des administrations

Le catalogue est stocké dans la base métier `backend` : tables `registries`,
`registry_services`, `questions`, `procedures` et `procedure_questions`.
Les trois bases des registres conservent leurs données propres aux citoyens.

Initialisation : `python -m scripts.seed_administration_catalog`, après `seed_demo`.
Cette initialisation est également exécutée au démarrage du backend. Elle ajoute
les éléments absents sans remplacer les modifications ultérieures.

| Fournisseur | Services REST implémentés déclarés |
| --- | --- |
| État civil | `identity`, `is-adult` |
| Justice | `nationality`, `criminal-record`, `criminal-record-current` |
| Trésor | `payment-status` |

| Administration demandeuse | Nouveau modèle de démarche |
| --- | --- |
| État civil | Préparation d’une copie d’acte de naissance |
| Justice | Pré-vérification d’un certificat de nationalité |
| Justice | Préparation d’un bulletin de casier judiciaire |
| Trésor | Vérification d’un paiement administratif |
| ONI | Pré-vérification d’une demande de CNIB |

Ces cinq modèles sont des propositions fonctionnelles, pas des règles légales
officielles. Ils sont ajoutés en brouillon, inactifs, sans attribution automatique
de permissions. La publication passe par le flux d’administration existant et sa
synchronisation X-Road. La déclaration en base ne prouve pas une publication X-Road.
Les démarches existantes de passeport et de concours sont conservées.

Chaque vérification précise le service, la clé booléenne attendue et la référence
documentaire requise. L’acte de naissance peut être demandé pour une démarche sans
être proposé comme identifiant permanent dans le profil. La référence de paiement
est transactionnelle. Pour `identity` et `payment-status`, la réponse booléenne
seule correspond au parcours utilisant une référence documentaire ; les anciens
parcours par identité peuvent retourner davantage d’attributs.
