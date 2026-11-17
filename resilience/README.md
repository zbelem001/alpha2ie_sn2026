# Couche résilience (bonus)

Responsable à désigner (proposition : Personne 3). Couche **bonus** de la carte du jury, mais « tenir quand un registre tombe » fait partie de l'épreuve en direct.

## Ce qui existe déjà

- Les connecteurs (`passerelle/connectors`) n'inventent jamais de réponse : un registre injoignable donne `unavailable`, jamais « oui ».
- La couche démarches reprend les vérifications interrompues sans appel en double (bail sur les tentatives, `attempt_lease_expired`, dans `execute_checks` de `demarches/app/api.py`) ; tests de reprise après panne dans `demarches/tests`.
- Banc X-Road : configuration persistante, reconnexion automatique des jetons ; si le serveur central tombe, les échanges continuent 10 minutes (validité de la configuration globale).

## À livrer

Un minimum vérifiable devant le jury : statut clair, jamais de « oui », consultation inscrite au journal, puis reprise automatique sans doublon. Tests de panne regroupés ici.
