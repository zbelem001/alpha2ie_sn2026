"""Infobip adapters for ordinary SMS and provider-managed 2FA PINs."""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)
PHONE_PATTERN = re.compile(r"^\+?[1-9][0-9]{7,14}$")
BASE_URL_PATTERN = re.compile(r"^(?:[a-z0-9-]+\.)*api\.infobip\.com$", re.IGNORECASE)


class SmsConfigurationError(RuntimeError):
    pass


class SmsDeliveryError(RuntimeError):
    def __init__(self, safe_code: str, *, detail: str | None = None, status_code: int | None = None):
        super().__init__(safe_code)
        self.safe_code = safe_code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class SmsSendResult:
    message_id: str
    status: str
    status_group: str
    destination: str | None = None


class SmsProvider(Protocol):
    def send(self, text: str) -> SmsSendResult: ...


@dataclass(frozen=True)
class InfobipSettings:
    api_key: str
    base_url: str
    sender: str
    test_phone_number: str

    @classmethod
    def from_environment(cls, *, require_api_key: bool = True) -> "InfobipSettings":
        api_key = os.getenv("INFOBIP_SMS_API_KEY", "").strip()
        base_url = os.getenv("INFOBIP_BASE_URL", "").strip().lower().rstrip("/")
        sender = os.getenv("INFOBIP_SENDER", "").strip()
        test_phone_number = os.getenv("TEST_PHONE_NUMBER", "").strip()

        if require_api_key and not api_key:
            raise SmsConfigurationError("infobip_sms_api_key_missing")
        if not BASE_URL_PATTERN.fullmatch(base_url):
            raise SmsConfigurationError("infobip_base_url_invalid")
        if not sender:
            raise SmsConfigurationError("infobip_sender_missing")
        if not PHONE_PATTERN.fullmatch(test_phone_number):
            raise SmsConfigurationError("infobip_test_phone_number_must_be_international_without_spaces")
        return cls(api_key=api_key, base_url=base_url, sender=sender, test_phone_number=test_phone_number)


class InfobipSmsProvider:
    """Infobip SMS v3 sender; every message is restricted to TEST_PHONE_NUMBER."""

    def __init__(self, settings: InfobipSettings, *, timeout: float = 12.0):
        self.settings = settings
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> "InfobipSmsProvider":
        return cls(InfobipSettings.from_environment())

    def send(self, text: str) -> SmsSendResult:
        if not text.strip() or "{" in text or "}" in text:
            raise SmsDeliveryError("sms_message_missing_or_unrendered")

        destination = self.settings.test_phone_number.removeprefix("+")
        url = f"https://{self.settings.base_url}/sms/3/messages"
        headers = {
            "Authorization": f"App {self.settings.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {
                    "destinations": [{"to": destination}],
                    "sender": self.settings.sender,
                    "content": {"text": text},
                }
            ]
        }

        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            detail = error.response.text[:2000].replace(self.settings.api_key, "[redacted]")
            raise SmsDeliveryError(
                "infobip_http_error",
                detail=detail,
                status_code=error.response.status_code,
            ) from error
        except httpx.HTTPError as error:
            raise SmsDeliveryError("infobip_transport_error", detail=type(error).__name__) from error

        try:
            response_body = response.json()
            result = response_body["messages"][0]
            message_id = result["messageId"]
            status = result["status"]["name"]
            status_group = result["status"]["groupName"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            detail = response.text[:2000].replace(self.settings.api_key, "[redacted]")
            raise SmsDeliveryError("infobip_invalid_response", detail=detail) from error

        if not all(isinstance(value, str) and value for value in (message_id, status, status_group)):
            raise SmsDeliveryError("infobip_invalid_response")
        return SmsSendResult(
            message_id=message_id,
            status=status,
            status_group=status_group,
            destination=self.settings.test_phone_number,
        )


@dataclass(frozen=True)
class InfobipOtpSettings:
    api_key: str
    base_url: str
    test_phone_number: str
    sender: str
    application_id: str
    consent_message_id: str
    registration_message_id: str

    @classmethod
    def from_environment(cls) -> "InfobipOtpSettings":
        values = {
            "api_key": os.getenv("INFOBIP_OTP_API_KEY", "").strip(),
            "base_url": os.getenv("INFOBIP_BASE_URL", "").strip().lower().rstrip("/"),
            "test_phone_number": os.getenv("TEST_PHONE_NUMBER", "").strip(),
            "sender": os.getenv("INFOBIP_SENDER", "").strip(),
            "application_id": os.getenv("INFOBIP_2FA_APPLICATION_ID", "").strip(),
            "consent_message_id": os.getenv("INFOBIP_2FA_CONSENT_MESSAGE_ID", "").strip(),
            "registration_message_id": os.getenv("INFOBIP_2FA_REGISTRATION_MESSAGE_ID", "").strip(),
        }
        if not values["api_key"]:
            raise SmsConfigurationError("infobip_otp_api_key_missing")
        if not BASE_URL_PATTERN.fullmatch(values["base_url"]):
            raise SmsConfigurationError("infobip_base_url_invalid")
        if not PHONE_PATTERN.fullmatch(values["test_phone_number"]):
            raise SmsConfigurationError("infobip_test_phone_number_must_be_international_without_spaces")
        if not values["sender"]:
            raise SmsConfigurationError("infobip_sender_missing")
        for key in ("application_id", "consent_message_id", "registration_message_id"):
            if not values[key]:
                raise SmsConfigurationError(f"{key}_missing")
        return cls(**values)


@dataclass(frozen=True)
class OtpSendResult:
    pin_id: str
    destination: str


class InfobipOtpProvider:
    """Infobip generates, delivers, and verifies OTPs through its 2FA API."""

    def __init__(self, settings: InfobipOtpSettings, *, timeout: float = 12.0):
        self.settings = settings
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> "InfobipOtpProvider":
        return cls(InfobipOtpSettings.from_environment())

    def send_pin(self, purpose: str, destination: str) -> OtpSendResult:
        if purpose not in {"consent", "registration"}:
            raise SmsConfigurationError("infobip_otp_purpose_invalid")
        if not PHONE_PATTERN.fullmatch(destination):
            raise SmsDeliveryError("infobip_otp_destination_invalid")
        if destination.removeprefix("+") != self.settings.test_phone_number.removeprefix("+"):
            raise SmsDeliveryError("infobip_trial_destination_must_match_test_phone")
        message_id = (
            self.settings.consent_message_id
            if purpose == "consent"
            else self.settings.registration_message_id
        )
        to = self.settings.test_phone_number.removeprefix("+")
        payload = {
            "applicationId": self.settings.application_id,
            "messageId": message_id,
            "from": self.settings.sender,
            "to": to,
        }
        response_body = self._post("/2fa/2/pin", payload)
        pin_id = response_body.get("pinId")
        if not isinstance(pin_id, str) or not pin_id:
            raise SmsDeliveryError("infobip_otp_invalid_response", detail=str(response_body)[:2000])
        return OtpSendResult(pin_id=pin_id, destination=self.settings.test_phone_number)

    def verify_pin(self, pin_id: str, pin: str) -> bool:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", pin_id):
            raise SmsDeliveryError("infobip_otp_pin_id_invalid")
        if not re.fullmatch(r"[0-9]{4,10}", pin):
            raise SmsDeliveryError("infobip_otp_pin_invalid")
        response_body = self._post(f"/2fa/2/pin/{pin_id}/verify", {"pin": pin})
        return response_body.get("verified") is True

    def _post(self, path: str, payload: dict) -> dict:
        headers = {
            "Authorization": f"App {self.settings.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                f"https://{self.settings.base_url}{path}",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as error:
            detail = error.response.text[:2000].replace(self.settings.api_key, "[redacted]")
            raise SmsDeliveryError(
                "infobip_otp_http_error", detail=detail, status_code=error.response.status_code
            ) from error
        except httpx.HTTPError as error:
            raise SmsDeliveryError("infobip_otp_transport_error", detail=type(error).__name__) from error
        except ValueError as error:
            raise SmsDeliveryError("infobip_otp_invalid_response") from error
        if not isinstance(body, dict):
            raise SmsDeliveryError("infobip_otp_invalid_response")
        return body


def build_sms_provider() -> SmsProvider:
    provider = os.getenv("SMS_PROVIDER", "simulated").strip().lower()
    if provider == "infobip":
        return InfobipSmsProvider.from_environment()
    raise SmsConfigurationError(f"sms_provider_unsupported:{provider or 'unset'}")
