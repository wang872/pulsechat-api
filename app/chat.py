from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import bad_request, forbidden, not_found
from app.models import Message, Room, RoomMember, User
from app.ws_manager import manager


def direct_key(user_a: int, user_b: int) -> str:
    lo, hi = sorted((user_a, user_b))
    return f"{lo}:{hi}"


def require_member(db: Session, room_id: int, user_id: int) -> RoomMember:
    member = db.scalar(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
    )
    if not member:
        raise forbidden("你不是该房间成员")
    return member


def serialize_message(db: Session, msg: Message) -> dict:
    sender = db.get(User, msg.sender_id)
    return {
        "id": msg.id,
        "room_id": msg.room_id,
        "sender_id": msg.sender_id,
        "sender_username": sender.username if sender else "unknown",
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def create_group(db: Session, user: User, name: str) -> Room:
    room = Room(name=name.strip(), is_direct=False, created_by=user.id)
    db.add(room)
    db.flush()
    db.add(RoomMember(room_id=room.id, user_id=user.id, last_read_message_id=0))
    db.commit()
    db.refresh(room)
    return room


def get_or_create_direct(db: Session, user: User, peer_username: str) -> Room:
    if peer_username == user.username:
        raise bad_request("不能和自己发起私聊")
    peer = db.scalar(select(User).where(User.username == peer_username))
    if not peer:
        raise not_found("对方用户不存在")
    key = direct_key(user.id, peer.id)
    existing = db.scalar(select(Room).where(Room.direct_key == key))
    if existing:
        return existing
    room = Room(
        name=f"{user.username},{peer.username}",
        is_direct=True,
        created_by=user.id,
        direct_key=key,
    )
    db.add(room)
    db.flush()
    db.add_all(
        [
            RoomMember(room_id=room.id, user_id=user.id, last_read_message_id=0),
            RoomMember(room_id=room.id, user_id=peer.id, last_read_message_id=0),
        ]
    )
    db.commit()
    db.refresh(room)
    return room


def list_rooms(db: Session, user: User) -> list[dict]:
    memberships = db.scalars(select(RoomMember).where(RoomMember.user_id == user.id)).all()
    result = []
    for m in memberships:
        room = db.get(Room, m.room_id)
        if not room:
            continue
        last = db.scalars(
            select(Message).where(Message.room_id == room.id).order_by(Message.id.desc()).limit(1)
        ).first()
        unread = db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.room_id == room.id, Message.id > (m.last_read_message_id or 0))
        ) or 0
        members = db.scalars(select(RoomMember).where(RoomMember.room_id == room.id)).all()
        names = {}
        ids = []
        for mem in members:
            u = db.get(User, mem.user_id)
            if u:
                names[u.id] = u.username
                ids.append(u.id)
        last_out = None
        if last:
            sender = db.get(User, last.sender_id)
            last_out = {
                "id": last.id,
                "content": last.content,
                "sender_username": sender.username if sender else "unknown",
            }
        result.append(
            {
                "id": room.id,
                "name": room.name,
                "is_direct": room.is_direct,
                "unread_count": int(unread),
                "online_members": manager.online_usernames(ids, names),
                "last_message": last_out,
            }
        )
    result.sort(key=lambda r: r["id"])
    return result


def list_messages(db: Session, user: User, room_id: int, limit: int) -> list[dict]:
    require_member(db, room_id, user.id)
    rows = db.scalars(
        select(Message).where(Message.room_id == room_id).order_by(Message.id.desc()).limit(limit)
    ).all()
    return [serialize_message(db, m) for m in reversed(rows)]


def send_message(db: Session, user: User, room_id: int, content: str) -> Message:
    require_member(db, room_id, user.id)
    msg = Message(room_id=room_id, sender_id=user.id, content=content.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def mark_read(db: Session, user: User, room_id: int) -> dict:
    member = require_member(db, room_id, user.id)
    last_id = db.scalar(select(func.max(Message.id)).where(Message.room_id == room_id)) or 0
    member.last_read_message_id = last_id
    db.commit()
    return {"room_id": room_id, "last_read_message_id": last_id}
