"""Textes modifiables des SMS envoyés par le backend."""
from __future__ import annotations

import math


CONSENT_REQUEST_TEMPLATE = (
    "Bonjour, votre consentement est requis pour {procedure_title} "
    "(réf. {case_reference}). Répondez sur la plateforme."
)
def render_consent_request(procedure_title: str | None, case_reference: str | None) -> str | None:
    """Render a personalized message; return None instead of leaking placeholders."""
    if not procedure_title or not case_reference:
        return None
    try:
        message = CONSENT_REQUEST_TEMPLATE.format(
            procedure_title=procedure_title.strip(),
            case_reference=case_reference.strip(),
        ).strip()
    except (KeyError, ValueError):
        return None
    if not procedure_title.strip() or not case_reference.strip() or "{" in message or "}" in message:
        return None
    return message


def message_character_warnings(message: str) -> list[str]:
    warnings: list[str] = []
    if len(message) > 160:
        warnings.append(f"{len(message)} caractères : le SMS dépasse 160 caractères.")
    if any(not character.isascii() for character in message):
        segments = max(1, math.ceil(len(message) / 70))
        warnings.append(
            f"Unicode détecté : environ {segments} segment(s), avec une limite de 70 caractères par segment."
        )
    return warnings
