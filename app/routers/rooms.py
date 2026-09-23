from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.chat import create_group, get_or_create_direct, list_rooms, mark_read
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import DirectCreateIn, RoomCreateIn, RoomOut

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomOut)
def create_room(body: RoomCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = create_group(db, user, body.name)
    return {
        "id": room.id,
        "name": room.name,
        "is_direct": room.is_direct,
        "unread_count": 0,
        "online_members": [],
        "last_message": None,
    }


@router.post("/direct", response_model=RoomOut)
def create_direct(body: DirectCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = get_or_create_direct(db, user, body.username)
    items = {r["id"]: r for r in list_rooms(db, user)}
    return items[room.id]


@router.get("", response_model=list[RoomOut])
def get_rooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_rooms(db, user)


@router.post("/{room_id}/read")
def read_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return mark_read(db, user, room_id)
