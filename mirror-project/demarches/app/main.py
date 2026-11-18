from fastapi import FastAPI

from app.api import router as api_router
from app.admin_api import router as admin_api_router
from app.phone_auth import router as phone_auth_router

app = FastAPI(title="Dites-le-nous une fois — API métier", version="0.1.0")
app.include_router(api_router)
app.include_router(admin_api_router)
app.include_router(phone_auth_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
