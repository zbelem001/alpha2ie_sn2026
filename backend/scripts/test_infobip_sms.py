"""Prévisualiser ou envoyer un SMS Infobip de test au numéro vérifié configuré."""
from __future__ import annotations

import argparse
import sys

from app.sms_provider import (
    InfobipSettings,
    InfobipSmsProvider,
    SmsConfigurationError,
    SmsDeliveryError,
)
from app.sms_templates import message_character_warnings, render_consent_request


def main() -> int:
    parser = argparse.ArgumentParser(description="Tester le SMS de consentement DLNUF avec Infobip.")
    parser.add_argument("--dry-run", action="store_true", help="afficher le SMS sans l'envoyer")
    parser.add_argument(
        "--procedure-title",
        default="Pré-vérification d’une demande de passeport ordinaire",
        help="démarche affichée dans le message de test",
    )
    parser.add_argument("--case-reference", default="TEST-01", help="référence fictive du dossier")
    args = parser.parse_args()

    try:
        settings = InfobipSettings.from_environment(require_api_key=not args.dry_run)
    except SmsConfigurationError as error:
        print(f"Configuration Infobip invalide : {error}", file=sys.stderr)
        return 2

    body = render_consent_request(args.procedure_title, args.case_reference)
    if body is None:
        print("Échec : démarche ou référence manquante, aucun SMS envoyé.", file=sys.stderr)
        return 2

    for warning in message_character_warnings(body):
        print(f"Avertissement : {warning}", file=sys.stderr)

    # La destination réelle du dossier n'est jamais utilisée dans ce script.
    print(f"Destinataire de test : {settings.test_phone_number}")
    if args.dry_run:
        print(f"DRY-RUN | {body}")
        print("Résumé : envoyés=0, échoués=0, prévisualisés=1")
        return 0

    try:
        result = InfobipSmsProvider(settings).send(body)
    except (SmsConfigurationError, SmsDeliveryError) as error:
        detail = f" — {error.detail}" if isinstance(error, SmsDeliveryError) and error.detail else ""
        print(f"ÉCHEC Infobip | {error}{detail}", file=sys.stderr)
        print("Résumé : envoyés=0, échoués=1")
        return 1

    print(f"ENVOYÉ | messageId={result.message_id} | statut={result.status} | groupe={result.status_group}")
    print("Résumé : envoyés=1, échoués=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
