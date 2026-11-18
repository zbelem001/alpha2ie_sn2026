"""Jetons de service, en écriture et en lecture. Fermé par défaut : sans jeton configuré, tout est refusé.

JOURNAL_WRITE_TOKENS="demarches=jeton-1,consentement-minimisation=jeton-2"
JOURNAL_READ_TOKENS="demarches=jeton-1,auditeur=jeton-3"

Le nom associé au jeton d'écriture devient la source de l'événement : une couche ne peut pas
écrire au nom d'une autre. En production, ces jetons seraient remplacés par l'authentification
mutuelle d'X-Road ou des identifiants clients OAuth.
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
            raise ValueError("Jetons du journal : « nom=jeton » attendu, séparés par des virgules")
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(f"Jeton du journal trop court pour « {name} » ({MIN_TOKEN_LENGTH} caractères au moins)")
        tokens[token] = name
    return tokens


def caller_for(token: str, tokens: Mapping[str, str]) -> str | None:
    """Nom associé au jeton, comparé en temps constant ; None si inconnu."""
    found = None
    for known, name in tokens.items():
        if hmac.compare_digest(known.encode("utf-8"), token.encode("utf-8")):
            found = name
    return found
