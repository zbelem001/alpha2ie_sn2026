"""Client du service de notifications, pour le backend.

Même règle que les connecteurs de registres : aucune méthode ne lève d'exception
pour un problème de service. Panne, délai dépassé ou réponse illisible donnent
le statut « unavailable » ; le backend relance plus tard avec le même
notification_id, ce qui n'envoie jamais deux fois le même message.

Contrat : contracts/schemas/notification-request.json, notification-response.json, sms-reply.json.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

import httpx

DEFAULT_SERVICE_URL = "http://notifications:8000"
DEFAULT_TIMEOUT_S = 3.0
SERVICE_STATUSES = frozenset({"sent", "failed", "invalid_request"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class NotificationClient:
    def __init__(
        self,
        base_url: str = DEFAULT_SERVICE_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT_S,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client or httpx.Client()

    # Envoi ---------------------------------------------------------------------------

    def send_sms(
        self,
        recipient: str,
        message: str,
        *,
        notification_id: str | None = None,
        reference: str | None = None,
        reply_choices: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Envoie un SMS. Pour une relance, repasser le même notification_id."""
        return self.send(
            {
                "notification_id": notification_id,
                "channel": "sms",
                "recipient": recipient,
                "message": message,
                "reference": reference,
                "reply_choices": list(reply_choices) if reply_choices is not None else None,
            }
        )

    def send_email(
        self,
        recipient: str,
        subject: str,
        message: str,
        *,
        notification_id: str | None = None,
        reference: str | None = None,
    ) -> dict[str, Any]:
        return self.send(
            {
                "notification_id": notification_id,
                "channel": "email",
                "recipient": recipient,
                "subject": subject,
                "message": message,
                "reference": reference,
            }
        )

    def send(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Envoie une demande conforme à notification-request.json ; ajoute notification_id s'il manque."""
        body = {key: value for key, value in payload.items() if value is not None}
        if not isinstance(body.get("notification_id"), str) or not body["notification_id"]:
            body["notification_id"] = str(uuid.uuid4())
        notification_id: str = body["notification_id"]

        def answer(status: str, detail: str) -> dict[str, Any]:
            return {"notification_id": notification_id, "status": status, "detail": detail, "responded_at": _now()}

        try:
            response = self._client.post(f"{self.base_url}/notifications", json=body, timeout=self.timeout)
        except httpx.TimeoutException:
            return answer("unavailable", "Délai d'attente dépassé")
        except httpx.HTTPError:
            return answer("unavailable", "Service de notifications injoignable")

        try:
            received = response.json()
        except ValueError:
            received = None
        if not isinstance(received, dict) or received.get("status") not in SERVICE_STATUSES:
            if response.is_client_error:
                return answer("invalid_request", f"Demande rejetée (HTTP {response.status_code})")
            return answer("unavailable", f"Réponse non conforme au contrat (HTTP {response.status_code})")
        if received["status"] != "invalid_request" and not response.is_success:
            return answer("unavailable", f"Réponse non conforme au contrat (HTTP {response.status_code})")

        result = {
            "notification_id": notification_id,
            "status": received["status"],
            "detail": received.get("detail") if isinstance(received.get("detail"), str) else None,
            "responded_at": received["responded_at"] if isinstance(received.get("responded_at"), str) else _now(),
        }
        if isinstance(received.get("duplicate"), bool):
            result["duplicate"] = received["duplicate"]
        return result

    # Réponses du citoyen ---------------------------------------------------------------

    def replies(self, after: int = 0, *, limit: int = 100) -> dict[str, Any]:
        """Réponses SMS arrivées après le numéro d'ordre `after`.

        Renvoie {"status": "ok" | "unavailable", "replies": [...], "cursor": n}. Garder `cursor`
        et le repasser comme `after` au prochain appel.
        """
        try:
            response = self._client.get(
                f"{self.base_url}/replies", params={"after": after, "limit": limit}, timeout=self.timeout
            )
            received = response.json() if response.is_success else None
        except (httpx.HTTPError, ValueError):
            received = None
        if (
            not isinstance(received, dict)
            or not isinstance(received.get("replies"), list)
            or not isinstance(received.get("cursor"), int)
        ):
            return {"status": "unavailable", "replies": [], "cursor": after}
        return {"status": "ok", "replies": received["replies"], "cursor": received["cursor"]}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NotificationClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def build_notifier(env: Mapping[str, str] | None = None) -> NotificationClient:
    """Client configuré par NOTIFICATION_SERVICE_URL et NOTIFICATION_TIMEOUT_S."""
    env = os.environ if env is None else env
    return NotificationClient(
        env.get("NOTIFICATION_SERVICE_URL") or DEFAULT_SERVICE_URL,
        timeout=float(env.get("NOTIFICATION_TIMEOUT_S") or DEFAULT_TIMEOUT_S),
    )
