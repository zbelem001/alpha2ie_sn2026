"""Boîte d'envoi en mémoire : messages remis, réponses du citoyen, idempotence.

Tout est perdu au redémarrage du conteneur : c'est une simulation. Le backend
garde sa propre trace (table notifications du guide).
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict, deque
from typing import Any

from notifications.common import utc_now_iso

from .models import NotificationRequest, SimulatedReply

# Destinataires fictifs toujours injoignables, pour tester l'échec d'envoi.
DEFAULT_UNREACHABLE = frozenset({"22670000099", "injoignable@exemple.bf"})
DEFAULT_CAPACITY = 1000

_COMPARED_FIELDS = ("channel", "recipient", "message", "subject", "reference", "reply_choices")


class ConflictError(ValueError):
    """Le notification_id a déjà servi pour un autre message."""


class ReplyTargetError(ValueError):
    """in_reply_to ne désigne pas un SMS reçu par ce numéro."""


class Outbox:
    def __init__(self, *, unreachable: frozenset[str] = DEFAULT_UNREACHABLE, capacity: int = DEFAULT_CAPACITY):
        self._unreachable = frozenset(value.lower() for value in unreachable)
        self._capacity = capacity
        self._lock = threading.Lock()
        self._seq = 0
        self._notifications: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._replies: deque[dict[str, Any]] = deque(maxlen=capacity)

    # Envoi ---------------------------------------------------------------------------

    def deliver(self, request: NotificationRequest) -> tuple[dict[str, Any], bool]:
        """Remet le message. Renvoie (enregistrement, nouveau) ; nouveau = False si déjà traité."""
        with self._lock:
            existing = self._notifications.get(request.notification_id)
            if existing is not None:
                if any(existing[field] != getattr(request, field) for field in _COMPARED_FIELDS):
                    raise ConflictError("notification_id déjà utilisé pour un autre message")
                return dict(existing), False

            failed = request.recipient.lower() in self._unreachable
            if failed:
                detail = "Destinataire injoignable (simulation) : message non remis."
            elif request.channel == "sms":
                detail = "Remis au téléphone simulé."
            else:
                detail = "Déposé dans la boîte de réception simulée."
            record = {
                "seq": self._next_seq(),
                "notification_id": request.notification_id,
                **{field: getattr(request, field) for field in _COMPARED_FIELDS},
                "status": "failed" if failed else "sent",
                "detail": detail,
                "sent_at": utc_now_iso(),
            }
            self._notifications[request.notification_id] = record
            while len(self._notifications) > self._capacity:
                self._notifications.popitem(last=False)
            return dict(record), True

    # Réponses du citoyen ---------------------------------------------------------------

    def record_reply(self, reply: SimulatedReply) -> dict[str, Any]:
        with self._lock:
            if reply.in_reply_to is not None:
                target = self._notifications.get(reply.in_reply_to)
                if target is None or not self._reached_phone(target, reply.sender):
                    raise ReplyTargetError("in_reply_to ne désigne pas un SMS reçu par ce numéro")
            else:
                target = next(
                    (
                        record
                        for record in reversed(self._notifications.values())
                        if self._reached_phone(record, reply.sender) and record["reply_choices"]
                    ),
                    None,
                )
            record = {
                "reply_id": str(uuid.uuid4()),
                "seq": self._next_seq(),
                "sender": reply.sender,
                "text": reply.text,
                "in_reply_to": target["notification_id"] if target else None,
                "reference": target["reference"] if target else None,
                "received_at": utc_now_iso(),
            }
            self._replies.append(record)
            return dict(record)

    # Lecture -------------------------------------------------------------------------

    def get(self, notification_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._notifications.get(notification_id)
            return self._with_answered(record, self._answered_ids()) if record else None

    def notifications(
        self,
        *,
        recipient: str | None = None,
        reference: str | None = None,
        channel: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Du plus récent au plus ancien."""
        with self._lock:
            answered = self._answered_ids()
            selected = []
            for record in reversed(self._notifications.values()):
                if recipient is not None and record["recipient"].lower() != recipient.lower():
                    continue
                if reference is not None and record["reference"] != reference:
                    continue
                if channel is not None and record["channel"] != channel:
                    continue
                selected.append(self._with_answered(record, answered))
                if len(selected) >= limit:
                    break
            return selected

    def replies(self, *, after: int = 0, sender: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Dans l'ordre d'arrivée, à partir du numéro d'ordre `after` exclu."""
        with self._lock:
            selected = [
                dict(reply)
                for reply in self._replies
                if reply["seq"] > after and (sender is None or reply["sender"] == sender)
            ]
            return selected[:limit]

    def thread(self, number: str) -> list[dict[str, Any]]:
        """Fil du téléphone : SMS reçus et réponses envoyées, dans l'ordre."""
        with self._lock:
            answered = self._answered_ids()
            items = [
                {"kind": "sms", **self._with_answered(record, answered)}
                for record in self._notifications.values()
                if self._reached_phone(record, number)
            ]
            items += [{"kind": "reply", **reply} for reply in self._replies if reply["sender"] == number]
            return sorted(items, key=lambda item: item["seq"])

    def reset(self) -> None:
        with self._lock:
            self._notifications.clear()
            self._replies.clear()

    # Interne -------------------------------------------------------------------------

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    @staticmethod
    def _reached_phone(record: dict[str, Any], number: str) -> bool:
        return record["channel"] == "sms" and record["status"] == "sent" and record["recipient"] == number

    def _answered_ids(self) -> set[str]:
        return {reply["in_reply_to"] for reply in self._replies if reply["in_reply_to"]}

    @staticmethod
    def _with_answered(record: dict[str, Any], answered: set[str]) -> dict[str, Any]:
        return {**record, "answered": record["notification_id"] in answered}
