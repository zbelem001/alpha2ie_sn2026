"""Jetons de service du registre des accords (côté demandeur). Fermé par défaut.

CONSENT_TOKENS="demarches=jeton-1" : couches autorisées à enregistrer, lire et retirer les accords.
La garde (côté détenteur, /holders/…) n'en demande pas : elle est appelée par la passerelle
et n'agit que sur présentation d'un accord valide. En production : authentification mutuelle
d'X-Road ou identifiants clients OAuth.
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping

MIN_TOKEN_LENGTH = 16


def parse_tokens(raw: str | None) -> dict[str, str]:
    """« nom=jeton,nom2=jeton2 » → {jeton: nom}."""
    tokens: dict[str, str] = {}
    for item in (raw or "").split(","):
        if not item.strip():
            continue
        name, separator, token = item.strip().partition("=")
        name, token = name.strip(), token.strip()
        if not separator or not name:
            raise ValueError("Jetons des accords : « nom=jeton » attendu, séparés par des virgules")
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(f"Jeton trop court pour « {name} » ({MIN_TOKEN_LENGTH} caractères au moins)")
        tokens[token] = name
    return tokens


def caller_for(token: str, tokens: Mapping[str, str]) -> str | None:
    found = None
    for known, name in tokens.items():
        if hmac.compare_digest(known.encode("utf-8"), token.encode("utf-8")):
            found = name
    return found
