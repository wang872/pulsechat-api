from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.chat import require_member, send_message, serialize_message
from app.db import get_session_factory
from app.models import User
from app.security import decode_access_token
from app.ws_manager import manager

router = APIRouter(tags=["ws"])


def _user_from_token(token: str | None) -> User | None:
    if not token:
        return None
    db = get_session_factory()()
    try:
        payload = decode_access_token(token)
        return db.get(User, int(payload["sub"]))
    except Exception:
        return None
    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    user = _user_from_token(token)
    if user is None:
        await websocket.close(code=4401)
        return

    user_id = user.id
    username = user.username
    await manager.connect(websocket, user_id)
    await manager.send(websocket, {"type": "presence", "user_id": user_id, "username": username, "online": True})

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            room_id = data.get("room_id")
            db = get_session_factory()()
            try:
                current = db.get(User, user_id)
                if current is None:
                    await manager.send(websocket, {"type": "error", "detail": "用户不存在"})
                    continue
                if msg_type == "join":
                    require_member(db, int(room_id), user_id)
                    manager.join_room(websocket, int(room_id))
                    await manager.send(websocket, {"type": "joined", "room_id": int(room_id)})
                    await manager.broadcast_room(
                        int(room_id),
                        {"type": "presence", "room_id": int(room_id), "user_id": user_id, "username": username, "online": True},
                        exclude=websocket,
                    )
                elif msg_type == "send":
                    if not manager.allow_send(user_id):
                        await manager.send(websocket, {"type": "error", "detail": "发送过于频繁"})
                        continue
                    require_member(db, int(room_id), user_id)
                    content = str(data.get("content") or "").strip()
                    if not content or len(content) > 2000:
                        await manager.send(websocket, {"type": "error", "detail": "消息内容不合法"})
                        continue
                    saved = send_message(db, current, int(room_id), content)
                    payload = {"type": "message", **serialize_message(db, saved)}
                    await manager.send(websocket, payload)
                    await manager.broadcast_room(int(room_id), payload, exclude=websocket)
                elif msg_type == "typing":
                    require_member(db, int(room_id), user_id)
                    await manager.broadcast_room(
                        int(room_id),
                        {"type": "typing", "room_id": int(room_id), "user_id": user_id, "username": username},
                        exclude=websocket,
                    )
                else:
                    await manager.send(websocket, {"type": "error", "detail": "未知事件类型"})
            except Exception as exc:
                await manager.send(websocket, {"type": "error", "detail": str(getattr(exc, "detail", exc))})
            finally:
                db.close()
    except WebSocketDisconnect:
        gone_id, rooms = manager.disconnect(websocket)
        for room_id in rooms:
            await manager.broadcast_room(
                room_id,
                {"type": "presence", "room_id": room_id, "user_id": gone_id, "username": username, "online": False},
            )
