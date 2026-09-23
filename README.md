# PulseChat API

一句话介绍：基于 FastAPI 的即时通讯后端，JWT 鉴权 + REST 拉历史 + WebSocket 实时消息，支持群聊/私聊、未读数、输入中和在线状态，默认 SQLite 即可演示。

## 技术栈

FastAPI · SQLAlchemy 2.0 · PyJWT · WebSocket · 进程内 Pub/Sub（接口可替换 Redis）· SQLite

## 核心设计

```
浏览器 A / B
    │  JWT
    ▼
REST 建房间 / 拉历史 / 标记已读
    │
WebSocket /ws?token=
    ├─ join   进入房间（校验成员）
    ├─ send   落库 + 房间广播
    ├─ typing 仅广播不落库
    └─ presence 上线/离线通知同房间成员
```

- **私聊幂等**：两个用户 id 排序生成 `direct_key`，A→B 与 B→A 是同一房间。
- **未读**：`last_read_message_id` 之后的消息计数。
- **限流**：每用户 2 秒最多 5 条。
- **水平扩展**：`Hub.publish` 可换成 Redis Pub/Sub，连接仍粘在本机。



## 本地运行

```powershell
cd g:\自动编程\pulsechat-api
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env
.venv\Scripts\python -m uvicorn app.main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- Demo（开两个窗口分别登录 alice / bob，密码 `123456`）: http://127.0.0.1:8000/static/index.html

```powershell
.venv\Scripts\python -m pytest
```

## API 表

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` `/auth/login` | 注册 / 登录 |
| GET | `/auth/me` | 当前用户 |
| POST | `/rooms` | 建群，创建者自动入群 |
| POST | `/rooms/direct` | `{username}` 获取或创建私聊 |
| GET | `/rooms` | 我的房间 + 未读 + 在线成员 + 最后一条 |
| GET | `/rooms/{id}/messages` | 历史消息 |
| POST | `/rooms/{id}/messages` | REST 发消息（测试/降级） |
| POST | `/rooms/{id}/read` | 标记已读 |
| WS | `/ws?token=` | 实时通道 |
| GET | `/health` | 健康检查 |

WebSocket JSON：

```json
{"type":"join","room_id":1}
{"type":"send","room_id":1,"content":"hi"}
{"type":"typing","room_id":1}
```

服务端事件：`joined` / `message` / `typing` / `presence` / `error`

生产环境请修改 `SECRET_KEY`。
