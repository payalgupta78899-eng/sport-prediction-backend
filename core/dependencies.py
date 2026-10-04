from fastapi import Depends, HTTPException, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from core.security import decode_token
from core.redis_client import get_redis
from models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token : str             = Depends(oauth2_scheme),
    db    : Session         = Depends(get_db),
    r                       = Depends(get_redis)
) -> User:
    credentials_exception = HTTPException(
        status_code = 401,
        detail      = "Could not validate credentials",
        headers     = {"WWW-Authenticate": "Bearer"}
    )

    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    if payload.get("type") != "access":
        raise HTTPException(401, "Wrong token type")

    # check if token is blacklisted (logged out)
    try:
        if r.get(f"blacklist:access:{token}"):
            raise HTTPException(401, "Token has been revoked")
    except Exception:
        pass  # Redis down — skip blacklist check, fail open

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(403, "Account deactivated")
    if user.is_banned:
        raise HTTPException(403, "Account has been banned")

    return user


def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["moderator", "admin"]:
        raise HTTPException(403, "Moderator or Admin access required")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return current_user


def get_optional_user(
    request : Request,
    db      : Session = Depends(get_db)
) -> Optional[User]:
    """Used for public routes that show extra data when logged in"""
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token   = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None
