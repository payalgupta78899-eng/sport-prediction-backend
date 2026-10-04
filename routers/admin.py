from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from core.dependencies import require_admin, get_current_user
from schemas import UserResponse, UserUpdateRole
from models import User, AuditLog
from services.audit_service import log_action
from services.cache_service import cache_service

router = APIRouter(prefix="/admin", tags=["Admin"])

ALLOWED_ROLES = ["user", "moderator", "admin"]


@router.get("/users", response_model=list[UserResponse])
def get_all_users(
    current_user : User    = Depends(require_admin),
    skip         : int     = Query(0,   ge=0),
    limit        : int     = Query(50,  ge=1, le=200),
    role         : Optional[str] = Query(None),
    is_banned    : Optional[bool] = Query(None),
    db           : Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_banned is not None:
        query = query.filter(User.is_banned == is_banned)
    return query.offset(skip).limit(limit).all()


@router.put("/users/{user_id}/ban")
def ban_user(
    user_id      : int,
    request      : Request,
    current_user : User    = Depends(require_admin),
    db           : Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot ban yourself")
    if user.role == "admin":
        raise HTTPException(403, "Cannot ban another admin")
    if user.is_banned:
        raise HTTPException(400, "User is already banned")

    user.is_banned            = True
    user.refresh_token_hash   = None  # force logout immediately

    log_action(
        db         = db,
        action     = "admin.user_banned",
        user_id    = current_user.id,
        entity     = "user",
        entity_id  = user_id,
        details    = {"banned_username": user.username},
        ip_address = request.client.host
    )

    db.commit()
    return {"message": f"User '{user.username}' has been banned"}


@router.put("/users/{user_id}/unban")
def unban_user(
    user_id      : int,
    request      : Request,
    current_user : User    = Depends(require_admin),
    db           : Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if not user.is_banned:
        raise HTTPException(400, "User is not banned")

    user.is_banned = False

    log_action(
        db         = db,
        action     = "admin.user_unbanned",
        user_id    = current_user.id,
        entity     = "user",
        entity_id  = user_id,
        details    = {"unbanned_username": user.username},
        ip_address = request.client.host
    )

    db.commit()
    return {"message": f"User '{user.username}' has been unbanned"}


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id      : int,
    body         : UserUpdateRole,
    request      : Request,
    current_user : User    = Depends(require_admin),
    db           : Session = Depends(get_db)
):
    if body.new_role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Role must be one of: {ALLOWED_ROLES}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot change your own role")

    old_role  = user.role
    user.role = body.new_role

    log_action(
        db         = db,
        action     = "admin.role_changed",
        user_id    = current_user.id,
        entity     = "user",
        entity_id  = user_id,
        details    = {
            "username": user.username,
            "old_role": old_role,
            "new_role": body.new_role
        },
        ip_address = request.client.host
    )

    db.commit()
    return {
        "message" : "Role updated",
        "username": user.username,
        "old_role": old_role,
        "new_role": body.new_role
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id      : int,
    request      : Request,
    current_user : User    = Depends(require_admin),
    db           : Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot delete yourself")
    if user.role == "admin":
        raise HTTPException(403, "Cannot delete another admin")

    username = user.username

    log_action(
        db         = db,
        action     = "admin.user_deleted",
        user_id    = current_user.id,
        entity     = "user",
        entity_id  = user_id,
        details    = {"deleted_username": username},
        ip_address = request.client.host
    )

    db.delete(user)
    db.commit()
    return {"message": f"User '{username}' permanently deleted"}


@router.get("/audit-logs")
def get_audit_logs(
    current_user : User    = Depends(require_admin),
    action       : Optional[str] = Query(None),
    user_id      : Optional[int] = Query(None),
    skip         : int     = Query(0,  ge=0),
    limit        : int     = Query(50, ge=1, le=200),
    db           : Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    logs = query.order_by(
        AuditLog.created_at.desc()
    ).offset(skip).limit(limit).all()

    return [
        {
            "id"        : log.id,
            "user_id"   : log.user_id,
            "action"    : log.action,
            "entity"    : log.entity,
            "entity_id" : log.entity_id,
            "details"   : log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        }
        for log in logs
    ]
