"""Development-only OTPs for exercising numeric entry without a messaging provider."""

from __future__ import annotations

import hashlib
import hmac
import os
from uuid import UUID


class OtpSimulationConfigurationError(RuntimeError):
    pass


def delivery_mode() -> str:
    provider = os.getenv("SMS_PROVIDER", "simulated").strip().lower()
    if provider == "simulated":
        if os.getenv("OTP_SIMULATION_EXPOSE_CODE", "false").strip().lower() != "true":
            raise OtpSimulationConfigurationError("otp_simulation_code_exposure_disabled")
        _secret()
        return "simulated"
    if provider == "infobip":
        return "infobip"
    raise OtpSimulationConfigurationError("otp_provider_not_supported")


def _secret() -> bytes:
    secret = os.getenv("OTP_SIMULATION_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise OtpSimulationConfigurationError("otp_simulation_secret_missing_or_too_short")
    return secret


def code_for(challenge_id: UUID, purpose: str) -> str:
    digest = hmac.new(_secret(), f"otp:{purpose}:{challenge_id}".encode(), hashlib.sha256).digest()
    return str(100000 + int.from_bytes(digest[:8], "big") % 900000)


def digest_code(challenge_id: UUID, purpose: str, code: str) -> str:
    return hmac.new(
        _secret(),
        f"verify:{purpose}:{challenge_id}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


def code_matches(challenge_id: UUID, purpose: str, code: str, expected_digest: str | None) -> bool:
    if not expected_digest:
        return False
    return hmac.compare_digest(digest_code(challenge_id, purpose, code), expected_digest)
