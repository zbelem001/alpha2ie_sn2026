"""Trésor simulé (paiement des démarches).

Faso Arzeka n'est pas intégrable pendant le hackathon : ce service le remplace.

Services :
- payment-status : « payé : oui/non » pour (subject.pivot_id, procedure), avec la référence du paiement.

Routes de démonstration (hors contrat, à ne pas déclarer dans X-Road) :
- POST /simulate/payments                   : enregistre un paiement reçu
- POST /simulate/payments/{reference}/pay   : marque un paiement en attente comme reçu
"""

from __future__ import annotations

import copy
import json
import secrets
import os
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from registries.common import (
    RegistryDefinition,
    RegistryRequest,
    ServiceResult,
    create_registry_app,
    resolve_by_identifier,
)
from registries.common.envelope import utc_now_iso
from registries.common.models import PIVOT_PATTERN
from registries.common.database import DatabaseRecords

ORGANIZATION = "BF/GOV/TRESOR/PAIEMENTS"
DATA_FILE = Path(__file__).parent / "data" / "payments.json"


class NewPayment(BaseModel):
    pivot_id: str = Field(pattern=PIVOT_PATTERN)
    procedure: str = Field(min_length=1, max_length=64)
    amount_xof: int = Field(gt=0)


def create_app(payments: list[dict[str, Any]] | None = None) -> FastAPI:
    if payments is None:
        payments = DatabaseRecords(os.environ["REGISTRY_DATABASE_URL"]) if os.getenv("REGISTRY_DATABASE_URL") else json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(payments, DatabaseRecords):
        payments = copy.deepcopy(payments)

    def payment_status(request: RegistryRequest) -> ServiceResult:
        if request.parameters.get("document_identifier"):
            payment = resolve_by_identifier(payments, request.parameters, "payment_reference", "reference", request.subject)
            if isinstance(payment, ServiceResult):
                return payment
            if payment.get("procedure") != request.procedure:
                return ServiceResult.not_found()
            return ServiceResult.ok({"paid": payment["status"] == "paid"})
        pivot_id = request.subject.pivot_id
        if not pivot_id or not request.procedure:
            return ServiceResult.invalid("payment-status exige subject.pivot_id et procedure")
        mine = [p for p in payments if p["pivot_id"] == pivot_id and p["procedure"] == request.procedure]
        if not mine:
            return ServiceResult.ok({"paid": False, "reference": None, "amount_xof": None})
        paid = [p for p in mine if p["status"] == "paid"]
        chosen = paid[-1] if paid else mine[-1]
        return ServiceResult.ok(
            {"paid": chosen["status"] == "paid", "reference": chosen["reference"], "amount_xof": chosen["amount_xof"]}
        )

    simulation = APIRouter(prefix="/simulate", tags=["démonstration"])

    @simulation.post("/payments", status_code=201)
    def record_payment(payment: NewPayment) -> dict[str, Any]:
        entry = {
            "reference": f"PAY-{date.today().year}-{secrets.token_hex(3).upper()}",
            **payment.model_dump(),
            "status": "paid",
            "paid_at": utc_now_iso(),
        }
        payments.append(entry)
        return entry

    @simulation.post("/payments/{reference}/pay")
    def confirm_payment(reference: str) -> dict[str, Any]:
        for entry in payments:
            if entry["reference"] == reference:
                entry["status"] = "paid"
                entry["paid_at"] = entry["paid_at"] or utc_now_iso()
                if isinstance(payments, DatabaseRecords):
                    payments.save(entry)
                return entry
        raise HTTPException(status_code=404, detail="Paiement inconnu")

    definition = RegistryDefinition(
        name="Trésor — paiements (simulé)",
        organization=ORGANIZATION,
        description=__doc__ or "",
        services={"payment-status": payment_status},
    )
    return create_registry_app(definition, extra_routers=[simulation])


app = create_app()
