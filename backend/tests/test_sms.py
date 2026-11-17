from app.sms import TwilioSettings, send_twilio_sms


def test_twilio_sender_posts_form_with_api_key_auth(monkeypatch):
    settings = TwilioSettings(
        account_sid="AC" + "1" * 32,
        api_key_sid="SK" + "2" * 32,
        api_key_secret="secret-for-test-only",
        messaging_service_sid="MG" + "3" * 32,
        from_number=None,
        demo_citizen_ref="ACTE:OUAGA:2004:01234",
        demo_to_number="+22670000000",
    )
    sent_request = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"sid": "SM" + "4" * 32}

    def fake_post(url, *, data, auth, timeout):
        sent_request.update(url=url, data=data, auth=auth, timeout=timeout)
        return Response()

    monkeypatch.setattr("app.sms.httpx.post", fake_post)

    message_sid = send_twilio_sms(settings, "+22670000000", "Une demande vous attend.")

    assert message_sid == "SM" + "4" * 32
    assert sent_request["url"].endswith(f"Accounts/{settings.account_sid}/Messages.json")
    assert sent_request["auth"] == (settings.api_key_sid, settings.api_key_secret)
    assert sent_request["data"] == {
        "To": "+22670000000",
        "Body": "Une demande vous attend.",
        "MessagingServiceSid": settings.messaging_service_sid,
    }
    assert sent_request["timeout"] == 8.0


def test_twilio_sender_uses_from_number_when_no_messaging_service(monkeypatch):
    settings = TwilioSettings(
        account_sid="AC" + "1" * 32,
        api_key_sid="SK" + "2" * 32,
        api_key_secret="secret-for-test-only",
        messaging_service_sid=None,
        from_number="+12025550123",
        demo_citizen_ref="ACTE:OUAGA:2004:01234",
        demo_to_number="+22670000000",
    )
    payload = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"sid": "SM" + "5" * 32}

    def fake_post(url, *, data, auth, timeout):
        payload.update(data)
        return Response()

    monkeypatch.setattr("app.sms.httpx.post", fake_post)

    send_twilio_sms(settings, "+22670000000", "Une demande vous attend.")

    assert payload["From"] == "+12025550123"
