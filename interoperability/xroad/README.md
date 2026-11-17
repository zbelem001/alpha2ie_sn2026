# Banc de test X-Road

Responsable : Personne 3. Réservé au développement : images de test NIIS, mots de passe par défaut, autorité de certification de test.

Le banc fait passer les appels du backend vers les registres simulés par X-Road, sans rien changer au backend : il suffit de passer `REGISTRY_CONNECTOR` de `direct` à `xroad`. Si le banc n'est pas prêt, `REGISTRY_CONNECTOR=direct` garde tout fonctionnel.

## Démarrer

Depuis la racine du dépôt :

```bash
docker compose --profile xroad up -d --build        # démarre et configure le banc, avec le reste
docker compose --profile xroad logs -f xroad-setup  # suivre la configuration
```

Une seule commande : le service `xroad-setup` démarre avec les serveurs, attend qu'ils répondent, configure ce qui manque, puis s'arrête. Le banc est prêt quand son journal affiche « Banc X-Road prêt en … s » (et `docker compose --profile xroad ps -a xroad-setup` indique `Exited (0)`). Pour que `docker compose up -d --build` suffise, sans `--profile` : `COMPOSE_PROFILES=xroad` dans `.env`.

- **Démarrage** : 5 à 9 minutes avant que les quatre serveurs répondent (quatre serveurs Java démarrent en même temps). `up -d` rend la main tout de suite ; `xroad-setup` attend jusqu'à 12 minutes.
- **Configuration** : environ 7 minutes la première fois (mesuré : 402 s, soit 12 minutes en tout avec le démarrage, d'un seul passage sur un banc neuf). Le script ([configuration/setup_bench.py](configuration/setup_bench.py)) est relançable : les étapes déjà faites sont sautées, et une relance sur un banc configuré ne fait que la vérification finale (une quinzaine de secondes). Les messages « en attente » sont normaux : une modification du serveur central n'atteint les Security Servers qu'avec la configuration globale suivante. En cas d'échec, Docker relance le script trois fois au plus ; à la main : `docker compose --profile xroad run --rm xroad-setup`.
- **Mémoire** : environ 5,3 Go de plus que le reste de l'environnement (serveur central 1,9 Go, chaque Security Server 1,6 à 1,7 Go). Docker Desktop doit disposer d'au moins 8 Go.
- **Persistance** : toute la configuration est dans des volumes nommés (autorité de test, serveur central, chaque Security Server). Elle survit à `stop` / `start`, à `down` / `up` et à la recréation des conteneurs. Les trois serveurs se reconnectent seuls à leur jeton au démarrage (`XROAD_TOKEN_PIN`) : sans cela, le serveur central ne signe plus la configuration globale, qui expire, et plus aucun échange ne passe (`server.clientproxy.global_conf_outdated`, constaté avant la correction).
- **Remise à zéro complète** : supprimer les conteneurs du banc, puis **tous** ses volumes ensemble. Ne jamais en supprimer une partie seulement : serveur central, Security Servers et autorité se reconnaissent par leurs clés et leurs certificats.

  ```bash
  docker compose --profile xroad rm -sf xroad-setup xroad-cs xroad-ca ss-registres ss-demandeurs
  docker volume rm dlnuf_xroad-ca-home dlnuf_xroad-ca-certs \
    dlnuf_xroad-cs-config dlnuf_xroad-cs-db dlnuf_xroad-cs-data \
    dlnuf_ss-registres-config dlnuf_ss-registres-db dlnuf_ss-demandeurs-config dlnuf_ss-demandeurs-db
  ```

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

Tout autre appel est refusé par X-Road, avant même d'atteindre le registre. Par exemple, l'ONI qui demande le casier judiciaire : X-Road renvoie `server.serverproxy.access_denied`, que le connecteur traduit en `refused`. Les droits se modifient dans `CONSUMERS`, en haut du script, puis on relance `docker compose --profile xroad run --rm xroad-setup`.

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

Déploiement et persistance, le 17/11/2026 :

| Situation | Résultat |
|---|---|
| `docker compose --profile xroad up -d --build` sur un banc neuf (autorité de test conservée) | `up -d` rend la main en 75 s ; banc configuré et vérifié 12 minutes après la commande, sans relance |
| Même commande sur un banc déjà configuré | `up -d` en 14 s ; `xroad-setup` saute toutes les étapes, prêt en 36 s |
| Conteneurs arrêtés 2 heures puis redémarrés, **avant** la correction | Configuration conservée, mais jeton du serveur central déconnecté : `global_conf_outdated`, plus aucun échange |
| `down` (tous les conteneurs supprimés) puis `up` **sans** `xroad-setup`, après la correction | Configuration conservée (volumes), jeton du serveur central reconnecté seul, premier appel `ok` |
| Durée de validité de la configuration globale | 10 minutes (lue sur `ss-demandeurs`) |

## Limites

- Images de test, autorité de certification de test, aucun secret réel.
- Image Security Server « slim » : pas de journal des messages ni de supervision X-Road. Le journal de nos échanges reste celui du backend.
- Un seul serveur central, sans serveur de configuration secondaire. La configuration globale qu'il signe est valable **10 minutes** (valeur par défaut d'X-Road, mesurée sur le banc) : si le serveur central tombe, les Security Servers continuent d'échanger au plus 10 minutes, puis refusent tout (`global_conf_outdated`). En production : serveur central en haute disponibilité, et durée de validité réglée en conséquence.
