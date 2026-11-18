"""Encryption and lookup fingerprints for citizen supplied document references."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken


class IdentifierVaultError(RuntimeError):
    pass


def _key_material() -> bytes:
    configured = os.getenv("CITIZEN_IDENTIFIER_ENCRYPTION_KEY", "").strip()
    if not configured:
        raise IdentifierVaultError("citizen_identifier_encryption_key_missing")
    try:
        material = base64.urlsafe_b64decode(configured.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise IdentifierVaultError("citizen_identifier_encryption_key_invalid") from error
    if len(material) != 32:
        raise IdentifierVaultError("citizen_identifier_encryption_key_invalid")
    return material


def encrypt_identifier(value: str) -> str:
    normalized = value.strip().upper()
    try:
        return Fernet(base64.urlsafe_b64encode(_key_material())).encrypt(normalized.encode()).decode()
    except (ValueError, UnicodeEncodeError) as error:
        raise IdentifierVaultError("citizen_identifier_encryption_failed") from error


def decrypt_identifier(ciphertext: str) -> str:
    try:
        return Fernet(base64.urlsafe_b64encode(_key_material())).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError, UnicodeEncodeError) as error:
        raise IdentifierVaultError("citizen_identifier_decryption_failed") from error


def identifier_digest(identifier_type: str, value: str) -> str:
    material = _key_material()
    lookup_key = hmac.new(material, b"dlnuf-citizen-identifier-index", hashlib.sha256).digest()
    normalized = f"{identifier_type.strip().lower()}:{value.strip().upper()}".encode()
    return hmac.new(lookup_key, normalized, hashlib.sha256).hexdigest()
