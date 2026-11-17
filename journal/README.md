# Couche journal de traçabilité

Couche obligatoire de la carte du jury. **Pas encore extraite** : responsable à désigner (proposition : Personne 2).

## Rôle

- Retrouver **chaque consultation** : qui a demandé quoi, quand, pour quelle démarche, sur quelle base.
- Recherche par citoyen, par demande et par date.
- Les refus et les pannes y figurent aussi, pas seulement les réponses positives.
- La vidéo imposée se termine sur l'usager qui retrouve la consultation dans son espace.

## Où se trouve le code aujourd'hui

- `demarches/app/api.py` : `_add_event` (écriture des événements) et `GET /v1/cases/{case_id}/journal` (`get_journal`).
- `demarches/app/admin_api.py` : `GET /v1/admin/audit` (journal de l'administration locale).
- Modèles `AuditEvent` et `AdministrationAuditEvent` dans `demarches/app/database/models.py`.

## À livrer

`openapi.yaml` (écriture d'un événement, recherche par citoyen, demande et date), le code et ses tests.
