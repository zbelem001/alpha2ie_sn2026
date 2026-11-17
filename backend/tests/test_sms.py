import pytest

import httpx

from app.sms_provider import (
    InfobipSettings,
    InfobipSmsProvider,
    SmsConfigurationError,
    SmsDeliveryError,
)
from app.sms_templates import message_character_warnings, render_consent_request


def settings():
    return InfobipSettings(
        api_key="test-api-key",
        base_url="test.api.infobip.com",
        sender="DLNUF",
        test_phone_number="+22656178448",
    )


def test_infobip_sender_uses_sms_v3_contract_and_only_test_destination(monkeypatch):
    recorded = {}

    class Response:
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "messages": [{
                    "messageId": "abc123",
                    "status": {"name": "PENDING_ACCEPTED", "groupName": "PENDING"},
                }]
            }

    def fake_post(url, *, headers, json, timeout):
        recorded.update(url=url, headers=headers, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("app.sms_provider.httpx.post", fake_post)
    result = InfobipSmsProvider(settings()).send("Bonjour, votre consentement est requis.")

    assert result.message_id == "abc123"
    assert result.status == "PENDING_ACCEPTED"
    assert recorded["url"] == "https://test.api.infobip.com/sms/3/messages"
    assert recorded["headers"]["Authorization"] == "App test-api-key"
    assert recorded["payload"] == {
        "messages": [{
            "destinations": [{"to": "22656178448"}],
            "sender": "DLNUF",
            "content": {"text": "Bonjour, votre consentement est requis."},
        }]
    }


def test_infobip_http_error_keeps_provider_response_and_redacts_api_key(monkeypatch):
    class Response:
        status_code = 401
        text = '{"requestError":"invalid test-api-key credential"}'

    def fake_post(*args, **kwargs):
        request = httpx.Request("POST", args[0])
        raise httpx.HTTPStatusError(
            "unauthorized", request=request, response=httpx.Response(
                401, text=Response.text, request=request
            )
        )

    monkeypatch.setattr("app.sms_provider.httpx.post", fake_post)
    with pytest.raises(SmsDeliveryError) as error:
        InfobipSmsProvider(settings()).send("Message")

    assert error.value.status_code == 401
    assert "invalid" in error.value.detail
    assert "test-api-key" not in error.value.detail


def test_invalid_test_number_is_rejected(monkeypatch):
    monkeypatch.setenv("INFOBIP_SMS_API_KEY", "key")
    monkeypatch.setenv("INFOBIP_BASE_URL", "test.api.infobip.com")
    monkeypatch.setenv("INFOBIP_SENDER", "DLNUF")
    monkeypatch.setenv("TEST_PHONE_NUMBER", "+226 56178448")

    with pytest.raises(SmsConfigurationError, match="infobip_test_phone_number"):
        InfobipSettings.from_environment()


def test_missing_configuration_is_reported(monkeypatch):
    for key in ("INFOBIP_SMS_API_KEY", "INFOBIP_BASE_URL", "INFOBIP_SENDER", "TEST_PHONE_NUMBER"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(SmsConfigurationError, match="infobip_sms_api_key_missing"):
        InfobipSettings.from_environment()


def test_template_personalizes_message_and_never_leaves_missing_placeholders():
    message = render_consent_request("Demande de passeport ordinaire", "AB12CD34")

    assert message is not None
    assert "Demande de passeport ordinaire" in message
    assert "AB12CD34" in message
    assert "{" not in message and "}" not in message
    assert render_consent_request(None, "AB12CD34") is None
    assert render_consent_request("   ", "AB12CD34") is None
    assert render_consent_request("Démarche {incomplète", "AB12CD34") is None


def test_sms_length_and_unicode_warnings():
    warnings = message_character_warnings("Bonjour, votre demande nécessite une réponse.")
    assert any("Unicode" in warning and "70" in warning for warning in warnings)
    assert any("160" in warning for warning in message_character_warnings("x" * 161))


def test_test_cli_dry_run_displays_custom_message_without_http(monkeypatch, capsys):
    from scripts.test_infobip_sms import main

    monkeypatch.setenv("INFOBIP_SMS_API_KEY", "")
    monkeypatch.setenv("INFOBIP_BASE_URL", "test.api.infobip.com")
    monkeypatch.setenv("INFOBIP_SENDER", "DLNUF")
    monkeypatch.setenv("TEST_PHONE_NUMBER", "+22656178448")
    monkeypatch.setattr("sys.argv", ["test_infobip_sms", "--dry-run", "--procedure-title", "Passeport"])
    monkeypatch.setattr(
        "app.sms_provider.httpx.post",
        lambda *args, **kwargs: pytest.fail("dry-run ne doit pas appeler Infobip"),
    )

    assert main() == 0
    captured = capsys.readouterr()
    assert "Passeport" in captured.out
    assert "TEST-01" in captured.out
    assert "Destinataire de test : +22656178448" in captured.out
    assert "{" not in captured.out and "}" not in captured.out
    assert "prévisualisés=1" in captured.out
