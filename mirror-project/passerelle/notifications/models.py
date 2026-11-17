"""Validation des demandes (contracts/schemas/notification-request.json) et des réponses du citoyen."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NOTIFICATION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
PHONE_PATTERN = r"^[0-9]{8,15}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
REPLY_CHOICE_PATTERN = r"^[0-9A-Za-z]{1,10}$"
# Un identifiant pivot désigne l'acte de naissance : il n'a rien à faire dans un SMS.
PIVOT_IN_TEXT = re.compile(r"ACTE:[A-Z]+:[0-9]{4}:[0-9]{5}", re.IGNORECASE)

SMS_MAX_LENGTH = 480
EMAIL_MAX_LENGTH = 5000
REPLY_MAX_LENGTH = 160


class NotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notification_id: str = Field(min_length=1, max_length=128, pattern=NOTIFICATION_ID_PATTERN)
    channel: Literal["sms", "email"]
    recipient: str
    message: str = Field(min_length=1)
    subject: str | None = Field(default=None, max_length=150)
    reference: str | None = Field(default=None, max_length=64)
    reply_choices: list[str] | None = Field(default=None, min_length=1, max_length=5)

    @model_validator(mode="after")
    def check_channel_rules(self) -> NotificationRequest:
        if PIVOT_IN_TEXT.search(self.message) or (self.subject and PIVOT_IN_TEXT.search(self.subject)):
            raise ValueError("le message contient un identifiant pivot ; n'y mettre que la référence du dossier")

        if self.channel == "sms":
            if not re.fullmatch(PHONE_PATTERN, self.recipient):
                raise ValueError("recipient : numéro de 8 à 15 chiffres attendu, sans « + » ni espaces")
            if len(self.message) > SMS_MAX_LENGTH:
                raise ValueError(f"message : {SMS_MAX_LENGTH} caractères au plus pour un SMS")
            if self.subject is not None:
                raise ValueError("subject : interdit pour un SMS")
            if self.reply_choices is not None:
                if len(set(self.reply_choices)) != len(self.reply_choices):
                    raise ValueError("reply_choices : valeurs en double")
                if not all(re.fullmatch(REPLY_CHOICE_PATTERN, choice) for choice in self.reply_choices):
                    raise ValueError("reply_choices : 1 à 10 lettres ou chiffres par choix")
        else:
            if not re.fullmatch(EMAIL_PATTERN, self.recipient):
                raise ValueError("recipient : adresse e-mail attendue")
            if len(self.message) > EMAIL_MAX_LENGTH:
                raise ValueError(f"message : {EMAIL_MAX_LENGTH} caractères au plus pour un e-mail")
            if self.reply_choices is not None:
                raise ValueError("reply_choices : réservé aux SMS")
        return self


class SimulatedReply(BaseModel):
    """Ce que le citoyen tape sur son téléphone simulé."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sender: str = Field(pattern=PHONE_PATTERN)
    text: str = Field(min_length=1, max_length=REPLY_MAX_LENGTH)
    in_reply_to: str | None = Field(default=None, max_length=128)
