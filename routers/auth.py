from fastapi import APIRouter, Depends, HTTPException, Response, Request, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import time

from database import get_db
from core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, hash_token
)
from core.redis_client import get_redis
from core.config import settings
from core.dependencies import get_current_user
from schemas import RegisterRequest, LoginRequest, TokenResponse, ChangePasswordRequest
from models import User
from services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refresh_token"


@router.post("/register", status_code=201)
def register(
    body    : RegisterRequest,
    request : Request,
    db      : Session = Depends(get_db)
):
 # pydantic already validated body before we reach here
 
    # check username taken
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "Username already taken")

    # check email taken
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        username = body.username,
        email    = body.email,
        password = hash_password(body.password),
        role     = "user"  # always user on register — never self-assign admin
    )
    db.add(user)

    log_action(
        db         = db,
        action     = "user.register",
        entity     = "user",
        details    = {"username": body.username, "email": body.email},
        ip_address = request.client.host
    )

    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
def login(
    body     : LoginRequest,
    response : Response,
    request  : Request,
    db       : Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == body.username).first()

    # same error for both wrong username and wrong password
    # never tell attacker which one is wrong
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Account deactivated. Contact support.")

    if user.is_banned:
        raise HTTPException(403, "Account banned. Contact support.")

    token_data = {
        "sub"     : str(user.id),
        "username": user.username,
        "role"    : user.role
    }

    access_token  = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # store hash of refresh token in DB
    # on new login from another device old token invalidated
    user.refresh_token_hash = hash_token(refresh_token)
    user.updated_at         = datetime.utcnow()

    log_action(
        db         = db,
        action     = "user.login",
        user_id    = user.id,
        entity     = "user",
        entity_id  = user.id,
        ip_address = request.client.host
    )

    db.commit()

    # send refresh token as httpOnly cookie
    # JavaScript CANNOT read this — XSS protection
    response.set_cookie(
        key      = REFRESH_COOKIE_NAME,
        value    = refresh_token,
        httponly = True,    # JS cannot access
        secure   = True,    # HTTPS only
        samesite = "lax",   # CSRF protection
        max_age  = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {
        "access_token": access_token,
        "token_type"  : "bearer"
    }


@router.post("/refresh")
def refresh_token(
    response      : Response,
    request       : Request,
    refresh_token : Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db            : Session       = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(401, "Refresh token not found")

    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(401, "Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(401, "Wrong token type")

    # verify token matches what we stored in DB
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, "User not found")

    if user.refresh_token_hash != hash_token(refresh_token):
        # token was already rotated — possible token theft
        log_action(
            db         = db,
            action     = "security.refresh_token_reuse",
            user_id    = user.id,
            details    = {"suspicious": True},
            ip_address = request.client.host
        )
        db.commit()
        raise HTTPException(401, "Token already used. Please login again.")

    if user.is_banned or not user.is_active:
        raise HTTPException(403, "Account is not active")

    token_data = {
        "sub"     : str(user.id),
        "username": user.username,
        "role"    : user.role
    }

    new_access_token  = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    # rotate refresh token — store new hash
    user.refresh_token_hash = hash_token(new_refresh_token)
    user.updated_at         = datetime.utcnow()
    db.commit()

    # set new refresh token cookie
    response.set_cookie(
        key      = REFRESH_COOKIE_NAME,
        value    = new_refresh_token,
        httponly = True,
        secure   = True,
        samesite = "lax",
        max_age  = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    response     : Response,
    request      : Request,
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db),
    r                      = Depends(get_redis)
):
    # get current access token to blacklist it
    auth_header  = request.headers.get("Authorization", "")
    access_token = auth_header.replace("Bearer ", "")

    # blacklist access token for its remaining TTL
    if access_token:
        payload = decode_token(access_token)
        if payload:
            remaining_ttl = int(payload["exp"] - time.time())
            if remaining_ttl > 0:
                try:
                    r.setex(f"blacklist:access:{access_token}", remaining_ttl, "1")
                except Exception:
                    pass

    # invalidate refresh token by clearing hash in DB
    current_user.refresh_token_hash = None
    current_user.updated_at         = datetime.utcnow()

    log_action(
        db        = db,
        action    = "user.logout",
        user_id   = current_user.id,
        entity    = "user",
        entity_id = current_user.id,
        ip_address = request.client.host
    )

    db.commit()

    # clear cookie
    response.delete_cookie(REFRESH_COOKIE_NAME)
    return {"message": "Logged out successfully"}


@router.post("/change-password")
def change_password(
    body         : ChangePasswordRequest,
    request      : Request,
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    if not verify_password(body.current_password, current_user.password):
        raise HTTPException(400, "Current password is incorrect")

    current_user.password            = hash_password(body.new_password)
    current_user.refresh_token_hash  = None  # invalidate all sessions
    current_user.updated_at          = datetime.utcnow()

    log_action(
        db         = db,
        action     = "user.password_changed",
        user_id    = current_user.id,
        entity     = "user",
        entity_id  = current_user.id,
        ip_address = request.client.host
    )

    db.commit()
    return {"message": "Password changed. Please login again."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id"        : current_user.id,
        "username"  : current_user.username,
        "email"     : current_user.email,
        "role"      : current_user.role,
        "is_banned" : current_user.is_banned,
        "created_at": current_user.created_at
    }
