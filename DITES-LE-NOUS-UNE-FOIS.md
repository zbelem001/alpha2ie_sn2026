# « Dites-le-nous une fois » — Guide du projet

Hackathon des Universités 2026 · Finale · Sujet 02 · Thème : l'Open Source

> Ce document explique **quoi construire**, **pourquoi** et **comment**, pour que toute l'équipe (et le jury) comprenne le projet rapidement.

---

## 1. Le projet en 30 secondes

Aujourd'hui, un citoyen court de guichet en guichet pour apporter des papiers (acte de naissance, certificat de nationalité, casier judiciaire…), souvent légalisés.

**Notre idée :** les administrations s'échangent elles-mêmes l'information, de façon **sécurisée, consentie et traçable**, et ne transmettent que **le strict nécessaire**.

Exemple : la Direction des transports demande « ce citoyen est-il majeur ? » et reçoit `majeur: true`. Pas de nom, pas d'adresse, pas de date de naissance, pas de dossier complet.

**Phrase de pitch :**
> « Nous ne faisons pas circuler les citoyens entre les guichets ; nous faisons circuler, de manière sécurisée, consentie et traçable, uniquement l'information nécessaire entre les administrations. »

---

## 2. Ce que le jury attend (sujet officiel)

| Exigence | Ce que ça veut dire pour nous |
|---|---|
| **Ne transmettre que l'utile** | Une question précise, une réponse minimale (« majeur : oui ») |
| **Montrer qui a consulté ses données** | Un écran lisible pour l'usager : qui, quoi, quand, pourquoi |
| **Tenir quand un registre tombe en panne** | La demande est conservée, retentée, sans doublon |
| **Données** | Registres **simulés fournis par le jury** (état civil, nationalité, casier), citoyens fictifs |
| **Épreuve en direct** | Impossible à préparer : le système doit être **générique et configurable** |
| **Bien commun** | Code sous **licence libre**, socle réutilisable par l'administration |

---

## 3. Périmètre : ce qu'on fait et ce qu'on ne fait pas

### Le cœur (à livrer et à démontrer)
1. Demande ciblée (question précise vers un registre)
2. Minimisation (réponse minimale uniquement)
3. Consentement du citoyen (autoriser, refuser, retirer, expiration)
4. Traçabilité visible par l'usager
5. Résilience (panne d'un registre, reprises, pas de doublons)
6. Socle réutilisable (API documentée, configuration, guide d'intégration)

### Hors périmètre (à mentionner en « pistes d'évolution » dans la doc)
- Mode hors ligne complet côté guichet (file chiffrée locale, synchronisation différée)
- USSD et appel vocal réels
- Assistant vocal complet en mooré, dioula, fulfuldé
- Biométrie, chiffrement local des postes
- Application mobile, reçus imprimés
- Lecture/extraction de PDF (OCR)
- Connexion à de vrais registres nationaux

> Pourquoi ce choix ? Le jury juge un parcours **complet et démontrable**, pas une liste de fonctionnalités à moitié faites.

---

## 4. Les acteurs

| Acteur | Rôle | Compte ? |
|---|---|---|
| **Citoyen (usager)** | Donne ou refuse son consentement, consulte son historique, peut retirer son accord | **Non obligatoire.** Identifié par son numéro de citoyen (+ code SMS) |
| **Administration demandeuse** (Transports, Mairie, Fonction publique…) | Ouvre des démarches et pose des questions autorisées | **Oui** : accès technique (clé d'API) |
| **Administration fournisseur** (État civil, Nationalité, Justice) | Détient un registre et définit quelles questions peuvent être posées dessus | **Oui** : accès technique (clé d'API) |
| **Agent de guichet** | Employé qui utilise l'application pour aider le citoyen | Compte agent rattaché à son administration |
| **Plateforme** | Orchestre, vérifie le consentement, journalise. **Ne stocke pas les données des citoyens** | — |

Une administration peut être **fournisseur, demandeur, ou les deux**.

---

## 5. Glossaire simple

- **Guichet** : le comptoir physique d'une administration, où un agent traite la démarche du citoyen. Pour la démo : une simple page web.
- **Registre** : base officielle qui détient des données (ex. état civil).
- **Démarche** : une raison de demander des pièces (permis, prise de service, concours…). C'est une **liste de pièces requises**.
- **Dossier** : une démarche ouverte pour un citoyen précis.
- **Question** : ce qu'on a le droit de demander à un registre (`est_majeur`, `casier_vierge`…).
- **Consentement** : accord du citoyen, limité à une administration, une démarche et des questions précises.
- **Minimisation** : ne renvoyer que la réponse nécessaire.
- **Journal** : historique infalsifiable de toutes les consultations.

---

## 6. Architecture

```
┌──────────────────────┐        ┌──────────────────────┐
│ Administrations      │        │ Portail usager       │
│ demandeuses          │        │ (consentement +      │
│ (Mairie, Transports) │        │  historique)         │
└──────────┬───────────┘        └──────────┬───────────┘
           │ API (clé / jeton)             │
           ▼                               ▼
┌─────────────────────────────────────────────────────┐
│            PLATEFORME D'INTEROPÉRABILITÉ            │
│                                                     │
│  1. Passerelle API (authentification, validation)   │
│  2. Moteur de consentement ──► base consentements   │
│  3. Orchestrateur de requêtes                       │
│       └─► file d'attente + nouvelles tentatives     │
│  4. Catalogue de questions et de démarches (config) │
│  5. Connecteurs de registres                        │
│       └─► calcul de la réponse minimale             │
│  6. Journal de traçabilité (append-only, chaîné)    │
│  7. Service de notification (SMS simulé)            │
└───────────────┬─────────────────────────────────────┘
                │ appels API (timeout, retry, circuit breaker)
     ┌──────────┼──────────────┐
     ▼          ▼              ▼
┌─────────┐ ┌───────────┐ ┌─────────┐
│ État    │ │Nationalité│ │ Casier  │   Registres simulés
│ civil   │ │           │ │         │   (fournis par le jury)
└─────────┘ └───────────┘ └─────────┘
```

**Règle d'or :** la plateforme **orchestre**, elle ne devient **jamais** une base centrale qui copie les données des citoyens.

---

## 7. Comment une requête se déroule (flux principal)

1. Un agent ouvre une **démarche** pour un citoyen (numéro de citoyen + type de démarche).
2. La plateforme affiche la **liste des pièces nécessaires**.
3. Le citoyen donne un **consentement groupé** (un seul accord pour toutes les questions de la démarche).
4. L'administration envoie ses questions à la plateforme.
5. La plateforme vérifie : **(a)** l'administration est authentifiée, **(b)** elle a le droit de poser cette question, **(c)** le consentement est valide (bonne personne, bonne question, non expiré).
6. Le **connecteur** interroge le registre.
   - Si le registre est en panne : statut « en attente », demande conservée, nouvelles tentatives automatiques.
7. Le connecteur **calcule la réponse minimale** et **supprime la donnée brute**.
8. Le **journal** enregistre l'événement, le citoyen peut le voir, l'administration reçoit `majeur: true`.

### Les trois réponses possibles
| Réponse | Sens |
|---|---|
| `true` / `false` | Réponse à la question |
| `inconnu` | Citoyen introuvable dans ce registre |
| `indisponible` | Registre en panne, demande mise en attente |

> Distinguer « non » de « je ne sais pas » est essentiel : refuser un dossier à cause d'un champ vide serait une erreur grave.

---

## 8. Le consentement en détail

### Principes
- Donné **avant** la consultation, pour **une démarche précise**.
- **Limité** : administration + démarche + liste de questions (jamais « tout accès »).
- **Temporaire** : expire à la fin de la démarche ou après une durée fixe (ex. 30 jours).
- **Révocable** à tout moment.
- **Tracé** : création, usage, retrait sont journalisés.
- **L'agent ne peut jamais consentir à la place du citoyen.** Il faut un geste que seul le citoyen peut faire (bouton touché par lui, code SMS, touche de téléphone, signature).

### Cas 1 : le citoyen est au guichet (cas rapide, quelques secondes)
1. L'agent ouvre la démarche.
2. L'écran affiche de grandes icônes et **lit la question à voix haute** (« La Direction des transports veut vérifier si vous êtes majeur. Vous êtes d'accord ? »).
3. Le citoyen touche la **coche verte** (oui) ou la **croix rouge** (non), ou saisit un code reçu par SMS.
4. La plateforme enregistre la preuve (canal, heure, langue, geste utilisé).

### Cas 2 : le citoyen n'est pas là (cas de repli)
1. L'administration découvre plus tard qu'il lui manque une information.
2. La plateforme ne trouve pas de consentement valide → requête **bloquée**, statut « en attente du citoyen ».
3. **La plateforme** (pas la mairie, pas l'administration) contacte le citoyen sur son **numéro vérifié** : SMS « Répondez 1 pour OUI, 2 pour NON », ou appel vocal automatisé.
4. Réponse enregistrée → la requête repart. Sans réponse : **rappel**, puis **expiration** (ex. 7 jours).
5. Refus : requête annulée, agent informé, tout est journalisé.

### Comment limiter les retards
1. **Consentement groupé** à l'ouverture du dossier (un seul code pour toutes les vérifications).
2. **Statut visible** (vert = terminé, orange = en attente, rouge = problème).
3. **Rappels automatiques et expiration**, pour qu'un dossier ne reste jamais bloqué indéfiniment.

### Personnes illettrées
- Messages **courts**, audio **préparés à l'avance** par question (français + langues locales).
- **Icônes et boutons** à la place de formulaires.
- **Agent d'accompagnement** présent, mais c'est le citoyen qui fait le geste.
- **Témoin** possible pour les cas fragiles (identité journalisée).
- Confirmation ensuite par SMS ou appel, avec la possibilité de retirer son accord.

> À coder : écran guichet (icônes, audio, boutons, preuve enregistrée). À simuler : SMS et appel vocal.

---

## 9. Démarches : « une démarche = un fichier de configuration »

C'est ce qui rend le socle **réutilisable** : le moteur est le même pour un permis, un concours ou une prise de service. Seule la liste des pièces change.

```yaml
demarche: prise_de_service
administration: fonction_publique
pieces_requises:
  - question: est_majeur        # état civil
  - question: est_burkinabe     # nationalité
  - question: casier_vierge     # justice
  - document: diplome           # hors registre, fourni par le citoyen
```

### Qui déclenche une démarche ?
**Toujours le citoyen est à l'origine** : pas de dossier ouvert = pas de requête possible. La plateforme ne dit jamais « cette personne pourrait vous intéresser » (ce serait de la surveillance).

Si c'est un employeur ou une administration qui ouvre le dossier sans le citoyen présent :
- le citoyen est **notifié immédiatement** (SMS) ;
- l'administration ne peut ouvrir que **les démarches de son propre catalogue** ;
- **aucune requête ne part sans consentement**.

Le dossier a un **statut global** calculé à partir des pièces (ex. 2 reçues sur 4, 1 en attente de consentement, 1 manquante).

---

## 10. Le catalogue de questions (déclaratif)

Défini par l'administrateur du **registre fournisseur** :

```yaml
est_majeur:
  registre: etat_civil
  champ_source: date_naissance
  regle: age >= 18
  reponse: boolean
  consentement_requis: true
  expiration_consentement: 30j
```

Puis les **droits** : quelles administrations ont le droit de poser quelle question (ex. Transports : majorité et casier, **pas** la filiation).

> Il n'y a pas de PDF à traiter : la plateforme se branche sur le registre (API ou base). Le document d'origine n'est jamais manipulé ni copié.

---

## 11. Papiers légalisés : que deviennent-ils ?

La légalisation servait à **prouver** que l'information est vraie. Dans notre système, la preuve vient **de la source** :

- la réponse est **signée numériquement** par le registre ;
- elle est **horodatée** ;
- elle est **tracée** dans le journal ;
- un **code de vérification ou QR code** permet à toute administration de la contrôler.

| Cas | Ce qui se passe |
|---|---|
| L'info existe dans un registre | Plus de papier : réponse minimale signée (**notre cas**) |
| L'info n'existe dans aucun registre | Le citoyen fournit encore un document (hors périmètre) |
| Le citoyen veut quand même un papier | Le registre peut émettre un document avec code de vérification |

**Limite à dire franchement :** le mécanisme technique est prêt, mais la **valeur légale** de la réponse numérique (et du consentement vocal) dépend de la réglementation du pays.

---

## 12. Traçabilité

### Modèle d'une entrée de journal
```json
{
  "id": "evt_001",
  "horodatage": "2026-11-16T14:03:00Z",
  "administration": "direction_transports",
  "usager": "cit_4821",
  "question": "est_majeur",
  "registre": "etat_civil",
  "demarche": "permis_123",
  "resultat": "succes",
  "hash_precedent": "ab12..."
}
```
Le **chaînage par hash** rend le journal infalsifiable (bon argument en démo).

### Ce que voit l'usager (en phrases, pas en codes)
> « La Direction des transports a consulté votre statut de majorité auprès de l'état civil, le 16 novembre 2026, pour votre demande de permis. »

Il peut aussi **retirer son consentement** depuis cet écran.

---

## 13. Résilience (panne d'un registre)

À démontrer **en direct** : on coupe un registre volontairement.

La plateforme doit :
1. **détecter** l'indisponibilité (timeout, circuit breaker) ;
2. afficher un **statut clair** (« en attente, registre indisponible »), jamais une erreur technique brute ;
3. **conserver** la demande dans une file ;
4. **informer** l'agent et le citoyen (notification simulée) ;
5. **reprendre automatiquement** quand le registre revient ;
6. **éviter les doublons** grâce à une **clé d'idempotence** (une même demande n'est jamais traitée deux fois).

---

## 14. Modèle de données (tables principales)

| Table | Contenu |
|---|---|
| `administrations` | id, nom, rôle (fournisseur / demandeur), clé d'API |
| `registres` | id, administration, type de connexion, URL / config |
| `questions` | id, registre, champ source, règle, type de réponse |
| `droits` | administration demandeuse, question autorisée |
| `demarches` | id, administration, liste de pièces requises |
| `dossiers` | id, citoyen, démarche, statut global, date d'ouverture |
| `consentements` | id, citoyen, administration, dossier, questions, preuve (canal, heure, langue), expiration, statut |
| `requetes` | id, dossier, question, statut, clé d'idempotence, nb de tentatives |
| `journal` | id, horodatage, acteur, question, registre, démarche, résultat, hash_precedent |
| `notifications` | id, citoyen, canal, message, statut |

> **À ne jamais stocker :** dates de naissance, casiers, actes complets ou toute donnée brute d'un registre.

---

## 15. API : points d'entrée à prévoir

| Endpoint (exemple) | Rôle |
|---|---|
| `POST /dossiers` | Ouvrir une démarche pour un citoyen |
| `GET /dossiers/{id}` | Voir le statut global et par pièce |
| `POST /consentements` | Enregistrer un consentement (avec preuve) |
| `DELETE /consentements/{id}` | Retirer un consentement |
| `POST /requetes` | Poser une question ciblée (retourne la réponse minimale ou « en attente ») |
| `GET /usagers/{id}/historique` | Historique lisible des consultations |
| `GET /admin/questions` / `POST /admin/questions` | Gérer le catalogue (fournisseur) |
| `GET /verification/{code}` | Vérifier une réponse signée (QR code) |

Documenter le tout en **OpenAPI**.

---

## 16. Interfaces à construire

1. **Écran agent (guichet)** : ouvrir un dossier, voir la liste des pièces, statut vert/orange/rouge, consentement du citoyen.
2. **Écran citoyen / consentement** : grandes icônes, lecture audio, boutons oui / non, progression « 1. Identité → 2. Autorisation → 3. Terminé ».
3. **Portail usager** : historique des consultations en phrases, bouton « retirer mon accord ».
4. **Écran « téléphone du citoyen »** (simulation SMS) à côté de l'écran agent, pour la démo.
5. **Écran d'administration** : connecter un registre, déclarer les questions, gérer les droits.

---

## 17. Pile technique suggérée (à adapter)

- **Back-end :** Python (FastAPI) ou Node.js
- **Base de données :** PostgreSQL (ou SQLite pour la démo)
- **File et nouvelles tentatives :** Redis, ou simple table de jobs avec un worker
- **Interfaces :** pages web simples
- **Livraison :** Docker Compose, README, spécification OpenAPI
- **Licence :** libre (ex. Apache 2.0 ou AGPL, à décider en équipe)

---

## 18. Plan de travail suggéré

### Étape 0 : Cadrage (avant de coder)
- [ ] Poser les questions au jury (voir section 21)
- [ ] Choisir la pile technique et la licence
- [ ] Répartir les rôles

### Étape 1 : Socle
- [ ] Modèle de données et base
- [ ] Authentification des administrations (clés d'API) et droits
- [ ] Catalogue de questions et de démarches (lecture de la config)

### Étape 2 : Cœur fonctionnel
- [ ] Connecteurs de registres (génériques, configurables)
- [ ] Calcul de la réponse minimale et suppression de la donnée brute
- [ ] Moteur de consentement (création, vérification, expiration, retrait)
- [ ] Journal chaîné par hash

### Étape 3 : Résilience
- [ ] Timeouts, nouvelles tentatives, circuit breaker
- [ ] File d'attente + clé d'idempotence
- [ ] Statuts clairs (`indisponible`, `en attente`)
- [ ] Test : couper un registre et vérifier la reprise sans doublon

### Étape 4 : Interfaces
- [ ] Écran agent et écran consentement (icônes, audio, boutons)
- [ ] Portail historique usager
- [ ] Simulation SMS

### Étape 5 : Bien commun
- [ ] Documentation d'API (OpenAPI)
- [ ] Guide d'intégration d'une nouvelle administration
- [ ] Jeux de données fictifs et scénarios de test
- [ ] Règles de consentement et modèle de journal documentés
- [ ] Section « Hypothèses », « Limites » et « Pistes d'évolution »

### Étape 6 : Démo et pitch
- [ ] Répéter le scénario de 5 minutes (section 19)
- [ ] Préparer un plan B si le réseau ou un composant échoue

---

## 19. Scénario de démo (≈ 5 minutes)

**Démarche choisie :** une seule, avec 3 questions (majorité, nationalité, casier).

1. **Avant / Après** (30 s) : mairie → tampon → transports → files d'attente **vs** un guichet, un consentement, une réponse signée.
2. **Cas rapide** (1 min) : l'agent ouvre le dossier, le citoyen valide sur l'écran (icônes + audio + coche verte). Statut orange → vert.
3. **Minimisation** (45 s) : montrer la requête et la réponse `majeur: true`, puis ce qui n'est **pas** transmis (nom, date de naissance…).
4. **Sans consentement** (45 s) : la requête est bloquée proprement, un SMS part (simulé), le citoyen répond OUI, la requête repart.
5. **Transparence** (45 s) : le citoyen voit l'historique en phrases, puis retire son consentement.
6. **Panne en direct** (1 min) : on coupe le registre, statut clair, demande conservée, on rallume, reprise automatique, **aucun doublon**.
7. **Réutilisabilité** (30 s) : on ajoute une nouvelle démarche ou question **par un simple fichier de configuration**.

---

## 20. Hypothèses et limites (à écrire dans la doc)

### Hypothèses
1. Chaque registre détient déjà ses données de façon structurée (base ou API).
2. Les citoyens ont un **identifiant commun** entre registres, ou une table de correspondance.
3. Les données des registres sont considérées comme **exactes** (la plateforme ne les corrige pas).
4. Chaque registre accepte d'exposer une API ou un accès contrôlé.

### Limites assumées
- La **valeur légale** des réponses numériques signées et du consentement vocal dépend de la réglementation.
- Dans la réalité, le consentement n'est pas toujours la seule base légale (certaines démarches obligatoires peuvent autoriser l'échange avec simple information du citoyen). Nous retenons le consentement, mis en avant par le sujet.
- Le mode hors ligne, l'USSD, les langues locales complètes et la biométrie sont des évolutions possibles, non livrées.

---

## 21. Questions à poser au jury dès que possible

1. Dans quel **format** les registres simulés seront-ils fournis (API REST, JSON, CSV, base de données) ?
2. Les registres partagent-ils un **identifiant commun** pour un même citoyen ?
3. Y aura-t-il des **données imparfaites** (champs vides, doublons) à gérer en direct ?
4. Quelle **licence libre** est attendue ou préférée ?
5. Le mode hors ligne et les langues locales sont-ils attendus, ou seulement la résilience côté registre ?

> Les réponses 1 et 2 conditionnent une bonne partie de l'architecture. Le fait que l'épreuve en direct soit imprévisible impose des **connecteurs configurables** plutôt que du code écrit en dur.

---

## 22. Livrables « bien commun »

- [ ] Code source sous licence libre
- [ ] Architecture claire (schéma + explication)
- [ ] Documentation d'API (OpenAPI)
- [ ] Jeux de données fictifs
- [ ] Règles de consentement
- [ ] Modèle de journal de traçabilité
- [ ] Scénarios de test
- [ ] Guide d'intégration pour une nouvelle administration ou un nouveau registre

**Objectif :** qu'une autre administration puisse ajouter son registre ou utiliser le socle **sans repartir de zéro**.

---

## 23. Résumé en 7 points

1. Le citoyen **ne circule plus**, c'est l'information qui circule.
2. On pose une **question précise** et on reçoit une **réponse minimale**.
3. **Pas de consentement valide, pas de requête.** Le citoyen autorise, voit tout et peut retirer.
4. L'agent **ne peut jamais consentir à la place** du citoyen.
5. Un **registre en panne** n'arrête rien : demande conservée, reprise automatique, pas de doublon.
6. Tout est **configurable** : une nouvelle démarche ou un nouveau registre = un fichier de config.
7. On livre un **bien commun** : code libre, documentation, jeux de test, guide d'intégration.
