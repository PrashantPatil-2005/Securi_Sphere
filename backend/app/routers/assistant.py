from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.ai.assistant import chat
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    body: AssistantChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settings.ai_assistant_enabled:
        raise HTTPException(status_code=503, detail="AI assistant is disabled")

    result = await chat(
        db,
        body.message,
        alert_id=body.alert_id,
        offense_id=body.offense_id,
        siem_query=body.siem_query,
    )
    return AssistantChatResponse(**result)
