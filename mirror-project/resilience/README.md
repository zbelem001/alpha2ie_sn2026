# Couche résilience (bonus)

Responsable : Personne 3. Couche **bonus** de la carte du jury, mais « tenir quand un registre tombe » fait partie de l'épreuve en direct.

Pas de service propre : cette couche regroupe les garanties en cas de panne, réparties dans les autres couches, leurs tests de bout en bout et la répétition de l'épreuve sur la pile Docker.

## Ce qui tient quand un registre tombe

| Garantie | Où | Testé |
|---|---|---|
| Statut clair, jamais « oui » : registre injoignable, trop lent ou réponse non conforme donnent `unavailable`, sans donnée | connecteurs (`passerelle/connectors`), garde (`consentement-minimisation`) | ici, et dans chaque couche |
| Chaque tentative au journal, des deux côtés : `registry_check` (demandeur) et `holder_response` (détenteur), reliés par l'identifiant de la requête | couche démarches, garde, couche journal | ici |
| **Reprise automatique**, sans le guichet : toutes les 15 s, les dossiers qui ont une vérification indisponible (ou un appel interrompu au-delà de son bail) et un accord actif sont repris | `demarches/app/retry.py` (`REGISTRY_RETRY_INTERVAL_S`, `REGISTRY_RETRY_MAX_ATTEMPTS`) | ici, et sur la pile |
| Sans appel en double : chaque demande est réservée par un bail avant l'appel, même si le guichet relance au même moment | `_run_checks` (couche démarches) | ici, et `demarches/tests` |
| Pas de reprise sans accord actif (accord retiré pendant la panne : aucun appel, aucun événement répété) | `demarches/app/retry.py` | ici |
| Journal ou registre des accords injoignable : rien ne sort de chez le détenteur, aucune action sans trace, reprise ensuite | couches démarches, consentement-minimisation, journal | ici |
| Banc X-Road : configuration persistante, reconnexion automatique des jetons ; si le serveur central tombe, les échanges continuent 10 minutes (validité de la configuration globale) | `passerelle/xroad` | sur le banc |

## Tests

Toute la chaîne d'une vérification, en mémoire : couche démarches → connecteur de la passerelle (`routing.detenteurs.yaml`) → garde → registres simulés, avec le registre des accords et le journal. Les registres sont derrière une « prise » qu'un test peut débrancher, ralentir ou faire mal répondre.

```bash
pip install -r requirements-dev.txt
python -m pytest        # 7 tests
```

- registre arrêté : âge confirmé, nationalité et casier « indisponibles », sans réponse ; consultations au journal des deux côtés ;
- reprise automatique : dossier terminé, une tentative échouée et une réussie par vérification, aucun appel de plus ensuite ;
- registre trop lent ; réponse non conforme (jamais « oui ») ;
- accord retiré pendant la panne : pas de reprise ;
- journal injoignable au moment d'inscrire la réponse : rien n'est confirmé sans trace, la demande est reprise après son bail ;
- registre des accords injoignable : aucun registre appelé.

## Répéter l'épreuve sur la pile

Pile démarrée (`docker compose up -d` dans `mirror-project/`), depuis `mirror-project/` :

```bash
python3 resilience/scenarios/registre_en_panne.py
```

Le script (bibliothèque standard seulement) arrête le registre de la Justice, fait lancer à Awa la démarche « concours direct » depuis son espace, montre les vérifications indisponibles et leurs traces au journal, redémarre le registre, puis attend la reprise automatique. Constaté le 18/11 : dossier terminé 15 s après le redémarrage, sans réponse obtenue deux fois. Code de sortie 0 si tout tient.

Pendant l'épreuve, à la main : `docker compose stop justice-registry`, puis `docker compose start justice-registry`.

## Limites

- La reprise s'arrête après 20 tentatives par demande (5 minutes environ) ; l'agent peut toujours relancer depuis le guichet.
- Une demande en erreur (`error`, réponse illisible côté couche démarches) n'est pas reprise automatiquement : elle demande un examen.
- Le banc X-Road n'a pas été relancé depuis `passerelle/` (5,3 Go de mémoire).
