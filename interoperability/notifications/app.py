"""Service de notifications simulé (SMS et e-mail).

Contrat (contracts/schemas/) :
- POST /notifications              : envoyer (notification-request -> notification-response)
- GET  /replies?after=<seq>        : réponses SMS du citoyen (sms-reply), dans l'ordre d'arrivée
- webhook vers NOTIFICATION_REPLY_WEBHOOK_URL : chaque réponse SMS, dès sa réception (sms-reply)

Consultation :
- GET  /notifications              : messages envoyés, du plus récent au plus ancien (filtres : recipient, reference, channel)
- GET  /notifications/{id}         : un message
- GET  /health

Démonstration (hors contrat) :
- GET  /                           : boîte d'envoi
- GET  /phone/{numéro}             : téléphone simulé du citoyen, avec réponse
- POST /simulate/replies           : le citoyen répond (utilisé par le téléphone simulé)
- GET  /simulate/phones/{numéro}/thread
- POST /simulate/reset             : tout effacer

Destinataires toujours injoignables : 22670000099 et injoignable@exemple.bf.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import ValidationError

from registries.common.envelope import utc_now_iso
from registries.common.logs import console_logger

from .models import PHONE_PATTERN, NotificationRequest, SimulatedReply
from .pages import outbox_page, phone_page
from .store import DEFAULT_UNREACHABLE, ConflictError, Outbox, ReplyTargetError

logger = console_logger("notifications")

WEBHOOK_TIMEOUT_S = 3.0


def mask(recipient: str) -> str:
    """Pour les journaux : jamais le destinataire complet."""
    if "@" in recipient:
        local, _, domain = recipient.partition("@")
        return f"{local[:1]}***@{domain}"
    return f"{recipient[:3]}{'*' * max(len(recipient) - 6, 0)}{recipient[-3:]}"


def _describe_validation_error(exc: ValidationError) -> str:
    # L'emplacement et la règle violée, jamais la valeur reçue.
    parts = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        message = error["msg"].removeprefix("Value error, ")
        parts.append(f"{location} : {message}" if location else message)
    return "; ".join(parts)


def create_app(
    *,
    webhook_url: str | None = None,
    http_client: httpx.Client | None = None,
    unreachable: frozenset[str] = DEFAULT_UNREACHABLE,
    latency_ms: int = 0,
) -> FastAPI:
    outbox = Outbox(unreachable=unreachable)
    client = http_client or httpx.Client()

    app = FastAPI(
        title="Notifications simulées (SMS, e-mail)",
        description=__doc__ or "",
        version="0.1.0",
    )

    def result(
        http_status: int,
        notification_id: str | None,
        status: str,
        detail: str | None,
        duplicate: bool | None = None,
    ) -> JSONResponse:
        body: dict[str, Any] = {
            "notification_id": notification_id,
            "status": status,
            "detail": detail,
            "responded_at": utc_now_iso(),
        }
        if duplicate is not None:
            body["duplicate"] = duplicate
        return JSONResponse(status_code=http_status, content=body)

    def forward(reply: dict[str, Any]) -> dict[str, str]:
        if not webhook_url:
            return {"status": "disabled", "detail": "Aucun webhook configuré : le backend lit GET /replies."}
        try:
            response = client.post(webhook_url, json=reply, timeout=WEBHOOK_TIMEOUT_S)
        except httpx.TimeoutException:
            return {"status": "failed", "detail": "délai dépassé"}
        except httpx.HTTPError:
            return {"status": "failed", "detail": "backend injoignable"}
        if response.is_success:
            return {"status": "delivered", "detail": f"HTTP {response.status_code}"}
        return {"status": "failed", "detail": f"HTTP {response.status_code}"}

    # Contrat -------------------------------------------------------------------------

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "up", "service": "notifications"}

    @app.post("/notifications")
    async def send(request: Request) -> JSONResponse:
        if latency_ms:
            await asyncio.sleep(latency_ms / 1000)
        try:
            body = await request.json()
        except ValueError:
            return result(400, None, "invalid_request", "Corps JSON invalide")

        raw_id = body.get("notification_id") if isinstance(body, dict) else None
        notification_id = raw_id if isinstance(raw_id, str) else None
        try:
            parsed = NotificationRequest.model_validate(body)
        except ValidationError as exc:
            return result(400, notification_id, "invalid_request", _describe_validation_error(exc))

        try:
            record, created = outbox.deliver(parsed)
        except ConflictError as exc:
            return result(409, parsed.notification_id, "invalid_request", str(exc))

        logger.info(
            "notification=%s channel=%s recipient=%s reference=%s status=%s duplicate=%s",
            parsed.notification_id,
            parsed.channel,
            mask(parsed.recipient),
            parsed.reference or "-",
            record["status"],
            not created,
        )
        return result(201 if created else 200, parsed.notification_id, record["status"], record["detail"], not created)

    @app.get("/replies")
    def list_replies(
        after: int = Query(0, ge=0, description="Numéro d'ordre (seq) de la dernière réponse déjà lue"),
        sender: str | None = Query(None, pattern=PHONE_PATTERN),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, Any]:
        replies = outbox.replies(after=after, sender=sender, limit=limit)
        return {"replies": replies, "cursor": replies[-1]["seq"] if replies else after}

    # Consultation --------------------------------------------------------------------

    @app.get("/notifications")
    def list_notifications(
        recipient: str | None = None,
        reference: str | None = None,
        channel: str | None = Query(None, pattern="^(sms|email)$"),
        limit: int = Query(50, ge=1, le=200),
    ) -> dict[str, Any]:
        return {
            "notifications": outbox.notifications(
                recipient=recipient, reference=reference, channel=channel, limit=limit
            )
        }

    @app.get("/notifications/{notification_id}")
    def get_notification(notification_id: str) -> dict[str, Any]:
        record = outbox.get(notification_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Notification inconnue")
        return record

    # Démonstration -------------------------------------------------------------------

    @app.post("/simulate/replies", tags=["démonstration"])
    def simulate_reply(body: dict[str, Any]) -> JSONResponse:
        try:
            parsed = SimulatedReply.model_validate(body)
        except ValidationError as exc:
            return JSONResponse(status_code=400, content={"detail": _describe_validation_error(exc)})
        try:
            reply = outbox.record_reply(parsed)
        except ReplyTargetError as exc:
            return JSONResponse(status_code=400, content={"detail": str(exc)})

        delivery = forward(reply)
        logger.info(
            "reply=%s sender=%s in_reply_to=%s webhook=%s",
            reply["reply_id"],
            mask(reply["sender"]),
            reply["in_reply_to"] or "-",
            delivery["status"],
        )
        return JSONResponse(status_code=201, content={"reply": reply, "webhook": delivery})

    @app.get("/simulate/phones/{number}/thread", tags=["démonstration"])
    def phone_thread(number: str) -> dict[str, Any]:
        if not re.fullmatch(PHONE_PATTERN, number):
            raise HTTPException(status_code=404, detail="Numéro invalide")
        return {"number": number, "items": outbox.thread(number)}

    @app.post("/simulate/reset", status_code=204, tags=["démonstration"])
    def reset() -> Response:
        outbox.reset()
        return Response(status_code=204)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def outbox_view() -> str:
        return outbox_page()

    @app.get("/phone/{number}", response_class=HTMLResponse, include_in_schema=False)
    def phone_view(number: str) -> str:
        if not re.fullmatch(PHONE_PATTERN, number):
            raise HTTPException(status_code=404, detail="Numéro invalide : 8 à 15 chiffres, sans « + »")
        return phone_page(number)

    return app


app = create_app(
    webhook_url=os.environ.get("NOTIFICATION_REPLY_WEBHOOK_URL") or None,
    latency_ms=int(os.environ.get("SIMULATED_LATENCY_MS") or 0),
)
