"""Garde placée devant chaque registre, côté détenteur : rien ne sort sans accord, et rien que l'utile.

Pour chaque appel reçu de la passerelle (POST /holders/{détenteur}/services/{service}) :
1. base de l'appel : l'accord désigné par l'en-tête X-Consent-Id doit être actif et couvrir ce
   demandeur (X-Road-Client), cette démarche, cette personne et ce service ; sinon « refused » ;
2. appel du registre avec le corps reçu (contrat des registres), sans l'accord ;
3. réduction de la réponse selon la règle du service (holders.yaml) ; une réponse qui ne s'y
   prête pas devient « unavailable », jamais « oui » ;
4. inscription au journal (holder_response ou holder_refusal), avant de répondre : journal
   injoignable, aucune donnée ne sort.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from journal_client import JournalUnavailable
from pydantic import ValidationError

from .consents import ConsentStore, is_active
from .holders import Holder, HolderCatalog, NonConforming, ServiceRule, reference_date
from .models import ConsentRecord
from .schemas import RegistryRequest

STATUSES = {"ok", "not_found", "ambiguous", "refused", "unavailable", "invalid_request"}
# Messages de la garde : le texte libre d'un registre ne sort pas (il pourrait contenir des données).
MESSAGES = {
    "not_found": "Aucune fiche ne correspond",
    "ambiguous": "Plusieurs fiches correspondent ; aucune donnée transmise",
    "refused": "Accès refusé par le registre",
    "unavailable": "Registre indisponible",
    "invalid_request": "Requête rejetée par le registre",
}
UNKNOWN_SUBJECT = "inconnu"


@dataclass(frozen=True)
class Answer:
    status: str
    data: dict[str, Any] | None = None
    message: str | None = None


def requester_matches(expected: str, requester: str | None) -> bool:
    """Le demandeur de l'accord, ou l'un de ses sous-systèmes X-Road (ex. …/FONCTION-PUBLIQUE/RECRUTEMENT)."""
    return bool(requester) and (requester == expected or requester.startswith(expected + "/"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class HolderGuard:
    def __init__(
        self,
        holders: Mapping[str, Holder] | HolderCatalog,
        consents: ConsentStore,
        journal: Any,
        *,
        client: httpx.Client | None = None,
        clients: Mapping[str, httpx.Client] | None = None,
        timeout: float = 3.0,
        today: Callable[[], date] = reference_date,
    ) -> None:
        # Catalogue relu à chaque appel (branchements), ou détenteurs fixés (tests).
        self._catalog = holders if isinstance(holders, HolderCatalog) else None
        self._static = None if self._catalog else dict(holders)
        self._consents = consents
        self._journal = journal
        self._client = client or httpx.Client()
        self._clients = dict(clients or {})
        self._timeout = timeout
        self._today = today

    @property
    def holders(self) -> dict[str, Holder]:
        return self._catalog.current() if self._catalog else self._static

    @property
    def catalog_error(self) -> str | None:
        return self._catalog.error if self._catalog else None

    # Réponse ------------------------------------------------------------------------------

    def handle(self, slug: str, service: str, body: Any, requester: str | None,
               consent_id: str | None) -> tuple[int, dict[str, Any]]:
        holder = self.holders.get(slug)
        organization = holder.organization if holder else slug
        request_id = body.get("request_id") if isinstance(body, dict) and isinstance(body.get("request_id"), str) else None

        def reply(http_status: int, answer: Answer) -> tuple[int, dict[str, Any]]:
            return http_status, {
                "request_id": request_id, "organization": organization, "service": service,
                "status": answer.status, "data": answer.data if answer.status == "ok" else None,
                "message": answer.message, "responded_at": utc_now_iso(),
            }

        if holder is None:
            return reply(404, Answer("invalid_request", message=f"Détenteur inconnu : {slug}"))
        rule = holder.services.get(service)
        if rule is None:
            return reply(404, Answer("invalid_request", message=f"Service inconnu : {service}"))
        try:
            request = RegistryRequest.model_validate(body)
        except ValidationError:
            return reply(400, Answer("invalid_request", message="Corps de requête non conforme au contrat des registres"))

        consent, refusal = self._authorize(holder, rule, request, requester, consent_id)
        try:
            if refusal is not None:
                self._trace(holder, rule, request, requester, consent, "holder_refusal", "refused", refusal, None)
                return reply(200, Answer("refused", message=refusal))
            answer = self._ask_registry(holder, rule, request, requester)
            self._trace(holder, rule, request, requester, consent, "holder_response", answer.status,
                        self._purpose(rule, answer), sorted(answer.data) if answer.data else None)
        except JournalUnavailable:
            return reply(200, Answer("unavailable", message="Journal de traçabilité indisponible : aucune donnée transmise"))
        return reply(400 if answer.status == "invalid_request" else 200, answer)

    # 1. Base de l'appel ----------------------------------------------------------------------

    def _authorize(self, holder: Holder, rule: ServiceRule, request: RegistryRequest, requester: str | None,
                   consent_id: str | None) -> tuple[ConsentRecord | None, str | None]:
        if rule.basis == "citizen_request":
            if request.procedure not in rule.procedures:
                return None, "Cette vérification n'est ouverte qu'au citoyen, pour sa propre démarche"
            return None, None
        if not consent_id:
            return None, "Aucun accord du citoyen n'accompagne la demande"
        try:
            consent = self._consents.get_record(UUID(consent_id))
        except ValueError:
            consent = None
        if consent is None:
            return None, "Accord inconnu"
        if consent.status == "revoked":
            return consent, "Accord retiré par le citoyen"
        if consent.status != "granted":
            return consent, "Accord refusé par le citoyen"
        if not is_active(consent, self._consents.now()):
            return consent, "Accord expiré"
        if request.procedure != consent.procedure_code:
            return consent, "L'accord ne couvre pas cette démarche"
        if not requester_matches(consent.requester_code, requester):
            return consent, "Le demandeur n'est pas celui de l'accord"
        if not consent.subject_ref.startswith("ACTE:"):
            return consent, "Identité du titulaire non vérifiable : aucun acte rattaché"
        if request.subject.pivot_id != consent.subject_ref:
            return consent, "La personne visée n'est pas celle de l'accord"
        if not any(item["holder_code"] == holder.organization and item["service_code"] == rule.service
                   for item in consent.scope):
            return consent, "L'accord ne couvre pas cette information"
        return consent, None

    # 2 et 3. Registre et réduction ---------------------------------------------------------

    def _ask_registry(self, holder: Holder, rule: ServiceRule, request: RegistryRequest,
                      requester: str | None) -> Answer:
        client = self._clients.get(holder.slug, self._client)
        url = f"{holder.registry_url.rstrip('/')}/services/{rule.called_service}"
        headers = {"X-Road-Client": requester} if requester else {}
        try:
            response = client.post(url, json=request.registry_payload(), headers=headers, timeout=self._timeout)
        except httpx.HTTPError:
            return Answer("unavailable", message="Registre injoignable")
        try:
            received = response.json()
        except ValueError:
            received = None
        status = received.get("status") if isinstance(received, dict) else None
        if status not in STATUSES or (status == "ok" and not isinstance(received.get("data"), dict)):
            if response.is_client_error:
                return Answer("invalid_request", message=f"Requête rejetée par le registre (HTTP {response.status_code})")
            return Answer("unavailable", message="Réponse du registre non conforme au contrat")
        if status != "ok":
            return Answer(status, message=MESSAGES[status])
        try:
            return Answer("ok", data=rule.reduce(received["data"], self._today()))
        except NonConforming:
            return Answer("unavailable", message="Réponse du registre non conforme à la règle de minimisation")

    # 4. Journal ------------------------------------------------------------------------------

    @staticmethod
    def _purpose(rule: ServiceRule, answer: Answer) -> str:
        if answer.status == "ok":
            return f"réponse réduite transmise : {rule.transmits()}"
        return f"aucune donnée transmise : {answer.message}"

    def _trace(self, holder: Holder, rule: ServiceRule, request: RegistryRequest, requester: str | None,
               consent: ConsentRecord | None, event_type: str, outcome: str, purpose: str,
               categories: list[str] | None) -> None:
        # Sujet de l'accord s'il y en a un, sinon celui de la requête : jamais d'autre donnée d'identité.
        subject = consent.subject_ref if consent else (request.subject.pivot_id or UNKNOWN_SUBJECT)
        question = None
        if consent is not None:
            question = next((item["question_code"] for item in consent.scope
                             if item["holder_code"] == holder.organization and item["service_code"] == rule.service), None)
        self._journal.append({
            "event_type": event_type, "subject_ref": subject,
            "case_id": consent.case_id if consent else None,
            "procedure_code": request.procedure,
            "actor_type": "administration", "actor_ref": holder.organization,
            "requester_code": requester,
            "requester_name": consent.requester_name if consent else None,
            "holder_code": holder.organization, "holder_name": holder.name,
            "question_code": question, "service_code": rule.service,
            "purpose": purpose[:200], "outcome": outcome, "data_categories": categories,
            "consent_id": str(consent.id) if consent else None,
            "correlation_id": request.request_id,
        })
