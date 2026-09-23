from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import unauthorized
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise unauthorized()
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except Exception:
        raise unauthorized()
    user = db.get(User, user_id)
    if not user:
        raise unauthorized()
    return user
