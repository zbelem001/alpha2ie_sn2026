"""Fabrique d'application FastAPI partagée par tous les registres simulés.

Chaque registre expose :
- POST /services/{service} : un service minimisé (corps : registry-request, réponse : registry-response) ;
- GET  /services           : la liste de ses services ;
- GET  /health             : son état.

Les URL /services/{service} sont celles déclarées comme services REST dans X-Road :
un appel à /r1/BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL/identity arrive ici sur /services/identity.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .envelope import ServiceResult, Status, build_envelope
from .logs import console_logger
from .models import RegistryRequest

ServiceHandler = Callable[[RegistryRequest], ServiceResult]

logger = console_logger("registry")


@dataclass(frozen=True)
class RegistryDefinition:
    name: str
    organization: str
    services: Mapping[str, ServiceHandler]
    description: str = ""


def _describe_validation_error(exc: ValidationError) -> str:
    # Uniquement l'emplacement et la règle violée : jamais la valeur reçue.
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc']) or 'corps'} : {error['msg']}" for error in exc.errors()
    )


def create_registry_app(
    definition: RegistryDefinition,
    *,
    extra_routers: Sequence[APIRouter] = (),
    latency_ms: int | None = None,
) -> FastAPI:
    organization = os.environ.get("ORGANIZATION", definition.organization)
    delay_ms = latency_ms if latency_ms is not None else int(os.environ.get("SIMULATED_LATENCY_MS") or 0)

    app = FastAPI(
        title=f"Registre simulé : {definition.name}",
        description=definition.description,
        version="0.1.0",
    )

    def reply(http_status: int, service: str, result: ServiceResult, request_id: str | None) -> JSONResponse:
        envelope = build_envelope(
            organization=organization, service=service, result=result, request_id=request_id
        )
        return JSONResponse(status_code=http_status, content=envelope)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "up", "registry": definition.name, "organization": organization}

    @app.get("/services")
    def list_services() -> dict[str, object]:
        return {"organization": organization, "services": sorted(definition.services)}

    @app.post("/services/{service}")
    async def call_service(service: str, request: Request) -> JSONResponse:
        if delay_ms:
            await asyncio.sleep(delay_ms / 1000)

        handler = definition.services.get(service)
        if handler is None:
            return reply(404, service, ServiceResult.invalid(f"Service inconnu : {service}"), None)

        try:
            body = await request.json()
        except ValueError:
            return reply(400, service, ServiceResult.invalid("Corps JSON invalide"), None)

        raw_id = body.get("request_id") if isinstance(body, dict) else None
        request_id = raw_id if isinstance(raw_id, str) else None

        try:
            parsed = RegistryRequest.model_validate(body)
        except ValidationError as exc:
            return reply(400, service, ServiceResult.invalid(_describe_validation_error(exc)), request_id)

        result = handler(parsed)
        logger.info(
            "service=%s client=%s xroad_id=%s procedure=%s request_id=%s status=%s",
            service,
            request.headers.get("X-Road-Client", "-"),
            request.headers.get("X-Road-Id", "-"),
            parsed.procedure or "-",
            request_id or "-",
            result.status.value,
        )
        http_status = 400 if result.status is Status.INVALID_REQUEST else 200
        return reply(http_status, service, result, request_id)

    for router in extra_routers:
        app.include_router(router)

    return app
