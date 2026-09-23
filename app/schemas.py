from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class RoomCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class DirectCreateIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)


class MessageCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    sender_id: int
    sender_username: str
    content: str
    created_at: str | None = None


class LastMessageOut(BaseModel):
    id: int
    content: str
    sender_username: str


class RoomOut(BaseModel):
    id: int
    name: str
    is_direct: bool
    unread_count: int
    online_members: list[str]
    last_message: LastMessageOut | None = None
