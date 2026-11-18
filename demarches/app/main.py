import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as api_router
from app.admin_api import router as admin_api_router
from app.phone_auth import router as phone_auth_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Reprise automatique des vérifications quand un registre revient (couche résilience).
    interval = float(os.environ.get("REGISTRY_RETRY_INTERVAL_S") or 0)
    worker = RetryWorker(SessionLocal, interval) if interval > 0 else None
    if worker:
        worker.start()
    yield
    if worker:
        worker.stop()


app = FastAPI(title="Dites-le-nous une fois — API métier", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)
app.include_router(admin_api_router)
app.include_router(phone_auth_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
