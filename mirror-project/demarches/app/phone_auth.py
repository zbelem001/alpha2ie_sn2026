"""Accès par téléphone : comptes Keycloak réels et preuve OTP à usage unique."""
import hashlib
import hmac
import os
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import RegistrationOtpRequest, RegistrationOtpVerify, request_registration_otp, verify_registration_otp, _utc
from app.database.connection import get_db
from app.database.models import RegistrationOtpChallenge
from app.keycloak_admin import KeycloakAdminClient

router = APIRouter(prefix="/v1/auth/phone", tags=["phone-access"])

class PhoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str = Field(pattern=r"^[0-9]{8}$")
    agent: bool = False

class VerifyInput(RegistrationOtpVerify):
    pass

class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    ticket: str = Field(min_length=64, max_length=64)
    pin: str = Field(pattern=r"^[0-9]{4,6}$")

def _secret() -> bytes:
    value = os.getenv("PHONE_REGISTRATION_SECRET") or os.getenv("OTP_SIMULATION_SECRET", "")
    if len(value) < 32:
        raise HTTPException(503, "La création de compte n’est pas configurée.")
    return value.encode()

def _ticket(challenge: RegistrationOtpChallenge) -> str:
    message = f"phone-registration:{challenge.id}:{challenge.phone_number}:{_utc(challenge.verified_at).isoformat()}"
    return hmac.new(_secret(), message.encode(), hashlib.sha256).hexdigest()

def _users(client: KeycloakAdminClient, phone: str):
    return client._request("GET", "/users", params={"username": phone, "exact": "true"}).json()

@router.post("/continue")
def continue_phone(body: PhoneInput, db: Session = Depends(get_db)):
    client = KeycloakAdminClient()
    if _users(client, body.phone):
        return {"step": "pin"}
    if body.agent:
        raise HTTPException(404, "Ce numéro n’a pas de compte agent. Contactez votre administrateur.")
    _secret()
    challenge = request_registration_otp(RegistrationOtpRequest(phone=body.phone), db)
    return {"step": "otp", **challenge}

@router.post("/verify")
def verify_phone(body: VerifyInput, db: Session = Depends(get_db)):
    _secret()
    result = verify_registration_otp(body, db)
    challenge = db.get(RegistrationOtpChallenge, body.challenge_id)
    return {**result, "ticket": _ticket(challenge)}

@router.post("/register", status_code=201)
def register_phone(body: RegisterInput, db: Session = Depends(get_db)):
    challenge = db.scalar(select(RegistrationOtpChallenge).where(RegistrationOtpChallenge.id == body.challenge_id).with_for_update())
    now = datetime.now(timezone.utc)
    if not challenge or not challenge.verified_at or _utc(challenge.expires_at) <= now:
        raise HTTPException(410, "La vérification a expiré. Recommencez avec votre numéro.")
    if not hmac.compare_digest(body.ticket, _ticket(challenge)):
        raise HTTPException(403, "Preuve de vérification invalide.")
    phone = challenge.phone_number.removeprefix("+226")
    if not re.fullmatch(r"[0-9]{8}", phone):
        raise HTTPException(422, "Numéro national invalide.")
    client = KeycloakAdminClient()
    if _users(client, phone):
        raise HTTPException(409, "Ce numéro a déjà un compte. Connectez-vous avec votre PIN.")
    client._request("POST", "/users", json={
        "username": phone, "enabled": True,
        "attributes": {"account_kind": ["citizen"], "phone_number": [challenge.phone_number],
                       "phone_number_verified": ["false" if os.getenv("SMS_PROVIDER", "").lower() == "simulated" else "true"]},
        "credentials": [{"type": "password", "value": body.pin, "temporary": False}],
    })
    user = _users(client, phone)[0]
    try:
        role = client._request("GET", "/roles/citizen").json()
        client._request("POST", f"/users/{user['id']}/role-mappings/realm", json=[role])
    except Exception:
        client._request("DELETE", f"/users/{user['id']}")
        raise
    db.delete(challenge)
    db.commit()
    return {"phone": phone, "created": True}
