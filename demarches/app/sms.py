"""SMS outbox orchestration, independent from the active SMS provider."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database.models import Notification
from app.sms_provider import SmsConfigurationError, SmsDeliveryError, build_sms_provider
from app.sms_templates import message_character_warnings

logger = logging.getLogger(__name__)


def dispatch_sms_notification(db: Session, notification: Notification) -> None:
    """Send one queued SMS; the platform notification remains independent."""
    if notification.channel != "sms" or notification.delivery_status != "queued":
        return
    try:
        provider = build_sms_provider()
        for warning in message_character_warnings(notification.message):
            logger.warning("SMS notification %s: %s", notification.id, warning)

        result = provider.send(notification.message)
        if result.status_group.upper() == "REJECTED":
            notification.delivery_status = "failed"
            notification.delivery_error = f"{result.status_group}:{result.status}"
            logger.error(
                "SMS provider rejected notification %s (messageId=%s, status=%s)",
                notification.id,
                result.message_id,
                result.status,
            )
        else:
            notification.provider_message_id = result.message_id
            notification.delivery_status = "sent"
            notification.delivery_error = None
            logger.info(
                "SMS provider accepted notification %s (messageId=%s, status=%s)",
                notification.id,
                result.message_id,
                result.status,
            )
    except SmsConfigurationError as error:
        notification.delivery_status = "failed"
        notification.delivery_error = str(error)
        logger.error("SMS notification %s configuration error: %s", notification.id, error)
    except SmsDeliveryError as error:
        notification.delivery_status = "failed"
        notification.delivery_error = error.safe_code
        logger.error(
            "SMS notification %s failed (HTTP %s): %s",
            notification.id,
            error.status_code or "n/a",
            error.detail or error.safe_code,
        )
    db.commit()
