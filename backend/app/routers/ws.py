"""WebSocket and overview endpoints."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import func, select

from app.database import read_session_factory
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.host import Host
from app.models.user import User
from app.security import create_ws_ticket, decode_token as jwt_decode
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        msg = json.loads(raw)
        if msg.get("type") != "auth" or not msg.get("token"):
            await websocket.close(code=4001)
            return
        token = msg["token"]
    except Exception:
        logger.debug("WebSocket auth handshake failed", exc_info=True)
        await websocket.close(code=4001)
        return

    try:
        payload = jwt_decode(token)
        if payload.get("type") not in ("access", "ws"):
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@router.post("/ws/token")
async def ws_token(user: User = Depends(get_current_user)):
    return {"token": create_ws_ticket(str(user.id)), "expires_in": 60}


@router.get("/overview")
async def overview(user: User = Depends(get_current_user)):
    async with read_session_factory()() as db:
        total_q, online_q, offline_q, active_q, critical_q = await asyncio.gather(
            db.execute(select(func.count()).select_from(Host)),
            db.execute(select(func.count()).select_from(Host).where(Host.status == "online")),
            db.execute(select(func.count()).select_from(Host).where(Host.status.in_(["offline", "critical"]))),
            db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open")),
            db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open", Alert.severity == "critical")),
        )
    return {
        "total_hosts": total_q.scalar_one(),
        "online_hosts": online_q.scalar_one(),
        "offline_hosts": offline_q.scalar_one(),
        "active_alerts": active_q.scalar_one(),
        "critical_alerts": critical_q.scalar_one(),
    }
