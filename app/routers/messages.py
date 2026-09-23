from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.chat import list_messages, send_message, serialize_message
from app.db import get_db
from app.deps import get_current_user
from app.errors import too_many
from app.models import User
from app.schemas import MessageCreateIn, MessageOut
from app.ws_manager import manager

router = APIRouter(tags=["messages"])


@router.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
def get_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_messages(db, user, room_id, limit)


@router.post("/rooms/{room_id}/messages", response_model=MessageOut)
def post_message(
    room_id: int,
    body: MessageCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not manager.allow_send(user.id):
        raise too_many()
    msg = send_message(db, user, room_id, body.content)
    return serialize_message(db, msg)
