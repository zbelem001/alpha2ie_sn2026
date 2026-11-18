from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models import RegistrationOtpChallenge
from app.phone_auth import RegisterInput, _ticket, register_phone

@pytest.fixture
def registration(monkeypatch):
    monkeypatch.setenv("OTP_SIMULATION_SECRET", "unit-test-private-secret-at-least-32-characters")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        challenge = RegistrationOtpChallenge(id=uuid4(), phone_number="+22680000000", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), resend_after=datetime.now(timezone.utc), verified_at=datetime.now(timezone.utc))
        db.add(challenge); db.commit()
        yield db, challenge
    engine.dispose()

def test_registration_rejects_forged_proof(registration):
    db, challenge = registration
    with pytest.raises(HTTPException) as error:
        register_phone(RegisterInput(challenge_id=challenge.id, ticket="0" * 64, pin="1234"), db)
    assert error.value.status_code == 403

def test_registration_rejects_unverified_challenge(registration):
    db, challenge = registration
    challenge.verified_at = None; db.commit()
    with pytest.raises(HTTPException) as error:
        register_phone(RegisterInput(challenge_id=challenge.id, ticket="0" * 64, pin="1234"), db)
    assert error.value.status_code == 410

def test_registration_rejects_expired_proof(registration):
    db, challenge = registration
    ticket = _ticket(challenge)
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1); db.commit()
    with pytest.raises(HTTPException) as error:
        register_phone(RegisterInput(challenge_id=challenge.id, ticket=ticket, pin="1234"), db)
    assert error.value.status_code == 410

def test_proof_is_bound_to_phone_and_validation(registration):
    _, challenge = registration
    ticket = _ticket(challenge)
    challenge.phone_number = "+22680000001"
    assert ticket != _ticket(challenge)
