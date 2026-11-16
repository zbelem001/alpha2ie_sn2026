# Parcours CNIB — proposition de parcours MVP

> **Document à partager pour validation.** Cette fiche combine les exigences du challenge, des informations publiées par l’Office national d’identification (ONI) et des choix proposés pour le prototype. Elle ne décrit pas un système d’échange actuellement utilisé par l’administration.

## 1. Objectif du prototype

Montrer comment l’ONI pourrait instruire une demande de CNIB en vérifiant les informations auprès des administrations qui les détiennent, avec le consentement du citoyen, sans lui faire transporter plusieurs fois les mêmes pièces. Le backend métier orchestre les vérifications, applique les règles de la démarche, minimise les résultats et alimente le journal consultable par le citoyen.

Le jeu de données de démonstration sera créé par l’équipe et contiendra uniquement des personnes et valeurs fictives. La personne 3 fournit les API et les registres simulés ; le backend les appellera via l’interface de connecteur convenue.

## 2. Ce que publie l’ONI

La page officielle de l’ONI indique, pour une demande de CNIB :

- pour une personne née au Burkina Faso, un extrait d’acte de naissance figure parmi les pièces demandées ;
- pour une personne née hors du Burkina Faso, un certificat de nationalité figure parmi les pièces demandées ;
- un formulaire est également mentionné dans les deux cas, avec des pièces supplémentaires pour certaines situations.

L’ONI décrit également le NIP et le numéro B comme références de la carte biométrique AES. Le numéro de série situé à gauche au verso n’est pas utilisable comme référence administrative. Le prototype ne doit contenir que des valeurs inventées.

Sources : [ONI — CNIB, pièces à fournir](https://oni.bf/nos-prestations/cnib/) ; [ONI — références de la CIB-AES](https://oni.bf/les-references-de-la-cib-aes/).

## 3. Parcours métier proposé

### Étape 1 — Création et consentement

1. L’agent ONI crée un dossier `demande-cnib` pour un citoyen fictif.
2. Le citoyen donne son consentement explicite à la démarche et aux consultations prévues. Le backend enregistre l’état, la date, la portée du consentement et la version du texte présenté.
3. Si le consentement est absent ou révoqué avant un appel, le backend bloque cet appel et journalise le refus. Le comportement d’une révocation après le début d’un échange doit être décidé par l’équipe.

### Étape 2 — Vérification de l’identité et du lieu de naissance

Le backend demande au registre d’état civil simulé de vérifier l’identité et de fournir seulement les éléments nécessaires à l’orientation du dossier, notamment la confirmation d’identité et le pays de naissance. Les données de recherche peuvent utiliser un identifiant pivot fictif défini dans le jeu de données.

### Étape 3 — Branche selon le lieu de naissance

| Résultat d’état civil | Branche proposée pour la démonstration | Résultat minimal visé pour l’ONI |
|---|---|---|
| Identité confirmée, naissance au Burkina Faso | Interroger le registre d’état civil sur l’existence/la validité de l’acte requis. Le scénario du challenge précise que la Justice n’est pas interrogée dans cette branche. | `identite_confirmee`, `lieu_naissance_pays: BF`, `acte_verifie: oui/non` et état de vérification. |
| Identité confirmée, naissance hors du Burkina Faso | Interroger un service simulé de nationalité pour vérifier le certificat/la nationalité requis. | `identite_confirmee`, `lieu_naissance_pays: autre`, `nationalite_verifiee: oui/non` et état de vérification. |
| Identité ambiguë ou introuvable | Ne pas transmettre de données d’identité au demandeur ; laisser le dossier à traiter. | État `ambiguous` ou `not_found`, sans attributs d’identité. |
| Registre indisponible | Garder le dossier en attente et permettre une reprise. | État `pending` avec motif `registry_unavailable`. |

**Portée de la proposition :** les pièces publiées par l’ONI motivent ces deux branches, mais les sources ne prouvent pas que ces vérifications interadministratives sont actuellement réalisées de cette manière. Le service de nationalité est donc un registre fictif/API à confirmer avec la personne 3 et l’équipe. Les exceptions (changement de nom, profession, perte/renouvellement, etc.) sont hors du premier MVP.

## 4. Données et minimisation

### Données d’entrée du dossier

- identifiant interne de demande ;
- identifiant du citoyen fictif et identifiant pivot de recherche ;
- démarche (`demande-cnib`), administration et agent demandeurs ;
- consentement correspondant et horodatage ;
- état et dates de création/mise à jour.

### Champs de carte à représenter dans le jeu fictif, si le scénario en a besoin

NIP, nom, prénoms, date et lieu de naissance, sexe, taille, dates d’établissement et d’expiration, lieu d’établissement, numéro B. Exclure le numéro de série explicitement non utilisable. Ne pas recopier tous ces champs dans chaque demande : ils appartiennent au registre simulé et ne sont retournés que si une étape les nécessite.

### Réponses au backend ONI

Retourner des affirmations ou résultats ciblés plutôt que la fiche entière : identité confirmée, acte vérifié, nationalité vérifiée, majorité si la règle de la démarche l’exige, et état de chaque vérification. Pour la majorité, le challenge donne l’exemple d’un booléen `majeur: true|false` au lieu de la date de naissance. La date de naissance n’est donc pas à transmettre lorsque le booléen suffit.

## 5. États et reprise après panne — règle proposée

État d’une vérification : `pending`, `confirmed`, `rejected`, `ambiguous`, `not_found`, `digitization_requested`, `unavailable`, `blocked` ou `error`.

État global de la demande :

- `received` : dossier créé ;
- `in_progress` : vérifications requises en cours ;
- `pending` : au moins une vérification obligatoire attend une réponse ou une reprise ;
- `completed` : toutes les vérifications obligatoires ont réussi ;
- `rejected` : une vérification obligatoire a échoué de façon définitive ;
- `cancelled` : dossier annulé selon une action autorisée.

Une panne de registre ne vaut pas rejet : la vérification passe à `unavailable` et le dossier à `pending`. Une relance réutilise la même demande et la même vérification logique, avec une nouvelle tentative horodatée, pour éviter les doublons. Une ambiguïté reste à traiter et ne libère pas les données d’identité à l’ONI. Les délais et le nombre maximal de relances sont des paramètres de démonstration à fixer par l’équipe, pas des délais réglementaires identifiés.

## 6. Journal visible par le citoyen

Pour chaque consultation ou tentative, enregistrer : citoyen et dossier, administration/agent demandeurs, registre/service consulté, démarche et base/finalité déclarées, catégories de données demandées, date/heure, résultat ou motif de blocage/indisponibilité, et identifiants de corrélation. Éviter d’enregistrer les valeurs brutes renvoyées par les registres. Le journal métier du citoyen reste distinct des journaux techniques X-Road.

## 7. Conservation des données

La loi burkinabè n°001-2021/AN pose le principe de ne pas conserver les données plus longtemps que nécessaire aux finalités du traitement (article 25). Les sources consultées ne donnent pas de durée chiffrée spécifique au dossier CNIB, au consentement ou au journal de ce prototype.

Pour le MVP : utiliser des données entièrement fictives, ne pas conserver les réponses brutes des registres, et définir une durée de démonstration/documentation à valider avec l’équipe. Ne pas présenter une durée provisoire comme une obligation légale. Source : [Loi n°001-2021/AN, texte consultable](https://natlex.ilo.org/dyn/natlex2/natlex2/files/download/113778/BFA-113778.pdf).

## 8. Scénarios de démonstration

1. **Succès — né au Burkina :** consentement accepté, identité et acte vérifiés, résultats minimisés, journal visible.
2. **Succès — né hors du Burkina :** consentement accepté, identité confirmée, nationalité vérifiée par le service simulé, résultats minimisés.
3. **Panne :** registre indisponible, dossier en attente, reprise sans doublon.
4. **Ambiguïté ou introuvable :** aucune donnée d’identité divulguée à l’ONI.
5. **Refus/révocation :** aucun appel au registre après refus ou révocation antérieure à l’appel ; événement de refus journalisé.

## 9. Points à valider avec l’équipe avant de figer les contrats

- Est-ce que le groupe accepte les deux branches proposées (état civil puis acte au Burkina / service simulé de nationalité hors Burkina) comme scénario de concours ?
- Quels champs fictifs et quel identifiant pivot le registre de la personne 3 utilisera-t-il ?
- Le consentement est-il donné une fois pour tout le dossier ou séparément pour chaque registre ? Que faire d’une révocation après le début du dossier ?
- Le résultat `majeur` est-il réellement nécessaire à la demande CNIB choisie ? Ne l’ajouter que si une règle de démarche le justifie.
- Quels délais/nombre de relances et quelle durée de conservation de démonstration retenir ?
- Si les branches CNIB paraissent trop hypothétiques pour le jury, choisir une autre démarche dont les vérifications et registres sont mieux définis par les données fournies.

Après validation, ces décisions alimenteront les schémas JSON, le contrat OpenAPI défini avec l’équipe, le modèle PostgreSQL et le connecteur métier.
