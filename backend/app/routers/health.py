"""Health check endpoints — liveness, readiness, startup."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.health import liveness, readiness, startup

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return await liveness()


@router.get("/health/live")
async def health_live():
    return await liveness()


@router.get("/health/startup")
async def health_startup():
    body = await startup()
    code = 200 if body["status"] == "started" else 503
    return JSONResponse(content=body, status_code=code)


@router.get("/health/ready")
async def health_ready():
    body = await readiness()
    code = 200 if body["status"] == "ready" else 503
    return JSONResponse(content=body, status_code=code)
