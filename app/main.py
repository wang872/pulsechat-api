from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import Base, get_engine, get_session_factory
from app.routers import auth, messages, rooms, ws
from app.seed import seed_data

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if get_settings().seed_on_startup:
        db = get_session_factory()()
        try:
            seed_data(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="PulseChat API",
    description="JWT + REST + WebSocket 即时通讯后端。",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(messages.router)
app.include_router(ws.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
