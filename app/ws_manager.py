from collections import defaultdict, deque
from time import monotonic
from typing import Any

from fastapi import WebSocket

from app.config import get_settings


class Hub:
    """进程内 pub/sub。多实例部署时把 publish 换成 Redis PUBLISH，subscribe 换成订阅线程。"""

    def __init__(self) -> None:
        self._subs: dict[str, list] = defaultdict(list)

    def subscribe(self, channel: str, callback) -> None:
        self._subs[channel].append(callback)

    def unsubscribe(self, channel: str, callback) -> None:
        subs = self._subs.get(channel, [])
        if callback in subs:
            subs.remove(callback)

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        for callback in list(self._subs.get(channel, [])):
            callback(payload)


class ConnectionManager:
    def __init__(self) -> None:
        self.hub = Hub()
        self.room_sockets: dict[int, set[WebSocket]] = defaultdict(set)
        self.user_sockets: dict[int, set[WebSocket]] = defaultdict(set)
        self.socket_user: dict[WebSocket, int] = {}
        self.socket_rooms: dict[WebSocket, set[int]] = defaultdict(set)
        self.online_users: set[int] = set()
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def is_online(self, user_id: int) -> bool:
        return user_id in self.online_users

    def online_usernames(self, user_ids: list[int], names: dict[int, str]) -> list[str]:
        return [names[uid] for uid in user_ids if uid in self.online_users and uid in names]

    def allow_send(self, user_id: int) -> bool:
        settings = get_settings()
        now = monotonic()
        window = settings.rate_limit_window_seconds
        q = self._hits[user_id]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= settings.rate_limit_messages:
            return False
        q.append(now)
        return True

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self.socket_user[websocket] = user_id
        self.user_sockets[user_id].add(websocket)
        self.online_users.add(user_id)

    def joined_rooms(self, websocket: WebSocket) -> set[int]:
        return self.socket_rooms.get(websocket, set())

    def join_room(self, websocket: WebSocket, room_id: int) -> None:
        self.room_sockets[room_id].add(websocket)
        self.socket_rooms[websocket].add(room_id)

    def disconnect(self, websocket: WebSocket) -> tuple[int | None, set[int]]:
        user_id = self.socket_user.pop(websocket, None)
        rooms = self.socket_rooms.pop(websocket, set())
        for room_id in rooms:
            self.room_sockets[room_id].discard(websocket)
        if user_id is not None:
            self.user_sockets[user_id].discard(websocket)
            if not self.user_sockets[user_id]:
                self.online_users.discard(user_id)
        return user_id, rooms

    async def send(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        await websocket.send_json(payload)

    async def broadcast_room(self, room_id: int, payload: dict[str, Any], exclude: WebSocket | None = None) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.room_sockets.get(room_id, ())):
            if ws is exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
        self.hub.publish(f"room:{room_id}", payload)


manager = ConnectionManager()
