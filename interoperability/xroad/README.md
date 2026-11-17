# Banc de test X-Road

Responsable : Personne 3. Réservé au développement : images de test NIIS, mots de passe par défaut, autorité de certification de test.

Le banc fait passer les appels du backend vers les registres simulés par X-Road, sans rien changer au backend : il suffit de passer `REGISTRY_CONNECTOR` de `direct` à `xroad`. Si le banc n'est pas prêt, `REGISTRY_CONNECTOR=direct` garde tout fonctionnel.

## Démarrer

Depuis la racine du dépôt :

```bash
docker compose --profile xroad up -d                  # démarre le banc avec le reste
docker compose --profile xroad run --rm xroad-setup   # configure le banc, attend qu'il soit prêt
```

- **Démarrage** : 5 à 9 minutes avant que les quatre conteneurs soient prêts (quatre serveurs Java démarrent en même temps). `xroad-setup` attend tout seul.
- **Configuration** : environ 7 minutes la première fois (mesuré : 402 s, soit 12 minutes en tout avec le démarrage, d'un seul passage sur un banc neuf). Le script ([configuration/setup_bench.py](configuration/setup_bench.py)) est relançable : les étapes déjà faites sont sautées, et une relance sur un banc configuré ne fait que la vérification finale (une quinzaine de secondes). Les messages « en attente » sont normaux : une modification du serveur central n'atteint les Security Servers qu'avec la configuration globale suivante.
- **Mémoire** : environ 5,3 Go de plus que le reste de l'environnement (serveur central 1,9 Go, chaque Security Server 1,6 à 1,7 Go). Docker Desktop doit disposer d'au moins 8 Go.
- **Persistance** : l'autorité de test garde ses clés dans un volume (`xroad-ca-home`). Le serveur central et les Security Servers gardent leur configuration dans leurs conteneurs, sans volume : elle est perdue si les conteneurs sont supprimés (`docker compose down`, ou changement d'image), et il faut alors relancer `xroad-setup`. Un arrêt suivi d'un redémarrage (`stop`, `start`) devrait la conserver ; ce cas n'a pas encore été vérifié.
- **Remise à zéro complète** : `docker compose --profile xroad rm -sf xroad-cs xroad-ca ss-registres ss-demandeurs`, puis `docker volume rm dlnuf_xroad-ca-home dlnuf_xroad-ca-certs`. Ne jamais supprimer seulement les volumes de l'autorité : les certificats déjà émis ne seraient plus reconnus.

## Topologie

| Conteneur | Rôle | Interface d'administration |
|---|---|---|
| `xroad-cs` | Serveur central de l'instance `BF` | https://localhost:4100 |
| `xroad-ca` | Autorité de certification de test, OCSP, horodatage | — |
| `ss-registres` | Security Server des administrations fournisseuses, et des services de gestion | https://localhost:4101 |
| `ss-demandeurs` | Security Server des administrations demandeuses | https://localhost:4102 |

Identifiants des interfaces : `xrd` / `secret`. Code PIN des jetons : `Secret1234`.

Deux Security Servers au lieu d'un par administration : c'est ce qui tient en mémoire sur un poste. X-Road permet à un Security Server d'héberger les sous-systèmes de plusieurs membres ; chacun signe avec son propre certificat.

## Membres et sous-systèmes

| Identifiant X-Road | Hébergé par | Rôle |
|---|---|---|
| `BF/GOV/CENTRALE/MANAGEMENT` | `ss-registres` | Services de gestion du réseau |
| `BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL` | `ss-registres` | `identity`, `identity-match`, `is-adult` |
| `BF/GOV/TRANSPORT/PERMIS` | `ss-registres` | `driving-licence` |
| `BF/GOV/JUSTICE/REGISTRES` | `ss-registres` | `nationality`, `criminal-record` |
| `BF/GOV/POLICE/PERTES` | `ss-registres` | `loss-declaration` |
| `BF/GOV/TRESOR/PAIEMENTS` | `ss-registres` | `payment-status` |
| `BF/GOV/ONI/CNIB` | `ss-demandeurs` | Demandeur : démarche CNIB |
| `BF/GOV/FONCTION-PUBLIQUE/RECRUTEMENT` | `ss-demandeurs` | Demandeur : démarche « prise de service » du guide |

Chaque service REST pointe vers `POST /services/{service}` du registre simulé correspondant.

## Droits d'accès (les « conventions » du banc)

| Demandeur | Services autorisés |
|---|---|
| `BF/GOV/ONI/CNIB` | `identity`, `identity-match`, `is-adult`, `nationality`, `loss-declaration`, `payment-status` |
| `BF/GOV/FONCTION-PUBLIQUE/RECRUTEMENT` | `is-adult`, `nationality`, `criminal-record` |

Tout autre appel est refusé par X-Road, avant même d'atteindre le registre. Par exemple, l'ONI qui demande le casier judiciaire : X-Road renvoie `server.serverproxy.access_denied`, que le connecteur traduit en `refused`. Les droits se modifient dans `CONSUMERS`, en haut du script, puis on relance `xroad-setup`.

## Brancher le backend

| Variable | Valeur |
|---|---|
| `REGISTRY_CONNECTOR` | `xroad` |
| `XROAD_SECURITY_SERVER_URL` | `http://ss-demandeurs:8080` depuis un conteneur, `http://localhost:8280` depuis la machine |
| `XROAD_CLIENT_ID` | `BF/GOV/ONI/CNIB` ou `BF/GOV/FONCTION-PUBLIQUE/RECRUTEMENT`, selon la démarche |

## Vérifier

Depuis la machine :

```bash
curl -s http://localhost:8280/r1/BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL/is-adult \
  -H 'X-Road-Client: BF/GOV/ONI/CNIB' -H 'Content-Type: application/json' \
  -d '{"subject": {"pivot_id": "ACTE:OUAGA:2004:01234"}}'
```

## Ce qui a été vérifié sur le banc

Avec le connecteur du backend (`REGISTRY_CONNECTOR=xroad`), le 17/11/2026 :

| Appel | Résultat |
|---|---|
| ONI → état civil `identity` (Awa) | `ok`, avec l'identifiant de message X-Road dans `transport_id` |
| ONI → état civil `identity` par critères (deux Moussa TRAORE) | `ambiguous`, aucune donnée transmise |
| ONI → état civil `is-adult` (personne absente) | `not_found` |
| ONI → Justice `nationality` (Issa, né à Abidjan) | `ok`, `burkinabe: true` |
| ONI → Trésor `payment-status` | `ok` |
| ONI → Justice `criminal-record` (hors convention) | `refused` |
| Fonction publique → Justice `criminal-record` | `ok` |
| Service inexistant | `invalid_request` |
| Identifiant pivot mal formé | `invalid_request` (réponse du registre, transmise par X-Road) |
| Registre de la Justice arrêté | `unavailable`, puis `ok` dès son redémarrage |

## Limites

- Images de test, autorité de certification de test, aucun secret réel.
- Image Security Server « slim » : pas de journal des messages ni de supervision X-Road. Le journal de nos échanges reste celui du backend.
- Un seul serveur central, sans serveur de configuration secondaire.
