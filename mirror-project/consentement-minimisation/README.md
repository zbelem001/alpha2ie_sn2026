# Couche consentement et minimisation

Couche obligatoire de la carte du jury. **Pas encore extraite** : responsable à désigner (proposition : Personne 2).

## Rôle

- Ne transmettre que l'utile : « majeur : oui », jamais la date de naissance.
- Appliquer les règles de consentement : qui peut demander quoi, pour quelle démarche, avec quel accord de l'usager.
- Fonctionner devant **n'importe quel registre conforme au contrat du jury**, y compris celui d'une autre équipe (épreuve en direct). Rien ne sort du côté du détenteur avant d'avoir été réduit à la réponse utile.

Enchaînement visé : registre → consentement et minimisation → journal → passerelle.

## Où se trouve le code aujourd'hui

- Consentement : `demarches/app/api.py`, routes `POST /v1/cases/{case_id}/consent` (`record_consent`), `DELETE /v1/cases/{case_id}/consent` (`revoke_consent`), consentement assisté par code (`request_assisted_consent_otp`, `verify_assisted_consent_otp`, `change_consent_channel`) et périmètre (`_consent_scope`). Modèles `Consent`, `ConsentQuestion`, `ConsentOtpChallenge` dans `demarches/app/database/models.py`.
- Minimisation : les registres simulés calculent eux-mêmes la réponse réduite (`registres/`) ; la couche démarches contrôle les réponses reçues dans `execute_checks`.

## À livrer

`schemas/consent.json` : schéma réservé (vide), à définir.

`openapi.yaml`, le code (service à part, placé côté détenteur, configuré par l'adresse d'un registre conforme), et ses tests.
