from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Message, Room, RoomMember, User
from app.security import hash_password


def seed_data(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)) is not None:
        return

    alice = User(username="alice", password_hash=hash_password("123456"))
    bob = User(username="bob", password_hash=hash_password("123456"))
    db.add_all([alice, bob])
    db.flush()

    general = Room(name="general", is_direct=False, created_by=alice.id)
    db.add(general)
    db.flush()
    db.add_all(
        [
            RoomMember(room_id=general.id, user_id=alice.id, last_read_message_id=0),
            RoomMember(room_id=general.id, user_id=bob.id, last_read_message_id=0),
        ]
    )
    db.add_all(
        [
            Message(room_id=general.id, sender_id=alice.id, content="Welcome to PulseChat."),
            Message(room_id=general.id, sender_id=bob.id, content="Hi Alice, this is the demo room."),
        ]
    )
    db.commit()
