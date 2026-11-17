"""Twilio SMS adapter for the consent-request outbox."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.database.models import Notification


class SmsConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class TwilioSettings:
    account_sid: str
    api_key_sid: str
    api_key_secret: str
    messaging_service_sid: str | None
    from_number: str | None
    demo_citizen_ref: str
    demo_to_number: str

    @classmethod
    def from_environment(cls) -> "TwilioSettings":
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        api_key_sid = os.getenv("TWILIO_API_KEY_SID", "").strip()
        api_key_secret = os.getenv("TWILIO_API_KEY_SECRET", "").strip()
        messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "").strip() or None
        from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip() or None
        demo_citizen_ref = os.getenv("TWILIO_DEMO_CITIZEN_REF", "").strip()
        demo_to_number = os.getenv("TWILIO_DEMO_TO", "").strip()
        if not all((account_sid, api_key_sid, api_key_secret)):
            raise SmsConfigurationError("twilio_credentials_missing")
        if not messaging_service_sid and not from_number:
            raise SmsConfigurationError("twilio_sender_missing")
        if not demo_citizen_ref or not demo_to_number:
            raise SmsConfigurationError("twilio_demo_recipient_missing")
        return cls(
            account_sid=account_sid,
            api_key_sid=api_key_sid,
            api_key_secret=api_key_secret,
            messaging_service_sid=messaging_service_sid,
            from_number=from_number,
            demo_citizen_ref=demo_citizen_ref,
            demo_to_number=demo_to_number,
        )


def send_twilio_sms(settings: TwilioSettings, to_number: str, body: str) -> str:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.account_sid}/Messages.json"
    form = {"To": to_number, "Body": body}
    if settings.messaging_service_sid:
        form["MessagingServiceSid"] = settings.messaging_service_sid
    elif settings.from_number:
        form["From"] = settings.from_number

    try:
        response = httpx.post(
            url,
            data=form,
            auth=(settings.api_key_sid, settings.api_key_secret),
            timeout=8.0,
        )
        response.raise_for_status()
        message_sid = response.json().get("sid")
    except (httpx.HTTPError, ValueError, TypeError) as error:
        # Do not persist or log provider response bodies, which can contain PII.
        raise RuntimeError("twilio_send_failed") from error
    if not isinstance(message_sid, str) or not message_sid:
        raise RuntimeError("twilio_invalid_response")
    return message_sid


def dispatch_sms_notification(db: Session, notification: Notification) -> None:
    """Send one queued demo SMS; the platform notification is independent."""
    if notification.channel != "sms" or notification.delivery_status != "queued":
        return
    try:
        settings = TwilioSettings.from_environment()
        if notification.recipient_ref != settings.demo_citizen_ref:
            raise SmsConfigurationError("twilio_demo_recipient_not_mapped")
        notification.provider_message_id = send_twilio_sms(
            settings,
            settings.demo_to_number,
            notification.message,
        )
        notification.delivery_status = "sent"
        notification.delivery_error = None
    except SmsConfigurationError as error:
        notification.delivery_status = "failed"
        notification.delivery_error = str(error)
    except RuntimeError as error:
        notification.delivery_status = "failed"
        notification.delivery_error = str(error)
    db.commit()
