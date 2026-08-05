"""Agent bundle download endpoints."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.utils.agent_bundle import resolve_agent_bundle, resolve_install_script

router = APIRouter(tags=["agent"])


@router.get("/install.sh")
async def serve_install_script():
    return FileResponse(resolve_install_script(), media_type="text/x-shellscript", filename="install.sh")


@router.get("/agent-bundle.tar.gz")
async def serve_agent_bundle():
    bundle = resolve_agent_bundle()
    return FileResponse(bundle, media_type="application/gzip", filename="agent-bundle.tar.gz")
