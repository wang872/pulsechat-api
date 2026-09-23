from fastapi.testclient import TestClient


def test_register_and_login(client: TestClient) -> None:
    reg = client.post("/auth/register", json={"username": "carol", "password": "carol123"})
    assert reg.status_code == 200
    login = client.post("/auth/login", json={"username": "carol", "password": "carol123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["username"] == "carol"


def test_group_and_direct_room(client: TestClient, login) -> None:
    alice_headers, _ = login("alice", "123456")
    created = client.post("/rooms", json={"name": "standup"}, headers=alice_headers)
    assert created.status_code == 200
    assert created.json()["is_direct"] is False

    first = client.post("/rooms/direct", json={"username": "bob"}, headers=alice_headers)
    second = client.post("/rooms/direct", json={"username": "bob"}, headers=alice_headers)
    assert first.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["is_direct"] is True


def test_send_message_unread_and_forbidden(client: TestClient, login) -> None:
    alice_headers, _ = login("alice", "123456")
    bob_headers, _ = login("bob", "123456")
    carol = client.post("/auth/register", json={"username": "dave", "password": "dave123"})
    assert carol.status_code == 200
    dave_headers, _ = login("dave", "dave123")

    rooms = client.get("/rooms", headers=alice_headers).json()
    general = next(r for r in rooms if r["name"] == "general")
    room_id = general["id"]

    sent = client.post(
        f"/rooms/{room_id}/messages",
        json={"content": "hello from alice"},
        headers=alice_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["content"] == "hello from alice"

    bob_rooms = client.get("/rooms", headers=bob_headers).json()
    bob_general = next(r for r in bob_rooms if r["id"] == room_id)
    assert bob_general["unread_count"] >= 1

    client.post(f"/rooms/{room_id}/read", headers=bob_headers)
    after_read = next(r for r in client.get("/rooms", headers=bob_headers).json() if r["id"] == room_id)
    assert after_read["unread_count"] == 0

    denied = client.get(f"/rooms/{room_id}/messages", headers=dave_headers)
    assert denied.status_code == 403
    denied_send = client.post(
        f"/rooms/{room_id}/messages",
        json={"content": "intruder"},
        headers=dave_headers,
    )
    assert denied_send.status_code == 403


def test_websocket_join_and_send(client: TestClient, login) -> None:
    alice_headers, alice_token = login("alice", "123456")
    rooms = client.get("/rooms", headers=alice_headers).json()
    room_id = next(r["id"] for r in rooms if r["name"] == "general")

    with client.websocket_connect(f"/ws?token={alice_token}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "presence"
        ws.send_json({"type": "join", "room_id": room_id})
        joined = ws.receive_json()
        assert joined["type"] == "joined"
        ws.send_json({"type": "send", "room_id": room_id, "content": "from websocket"})
        echoed = ws.receive_json()
        assert echoed["type"] == "message"
        assert echoed["content"] == "from websocket"
