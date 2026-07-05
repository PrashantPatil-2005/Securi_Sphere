from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.user import User
from app.services.ioc_lookup import lookup_virustotal

router = APIRouter(prefix="/ioc", tags=["ioc"])


@router.get("/lookup")
async def ioc_lookup(
    q: str = Query(..., min_length=3, max_length=128),
    user: User = Depends(get_current_user),
):
    return await lookup_virustotal(q)
