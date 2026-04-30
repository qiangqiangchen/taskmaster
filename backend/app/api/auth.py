"""
认证路由
- POST /api/auth/login     登录
- POST /api/auth/logout    登出
- GET  /api/auth/me        获取当前用户信息
- PUT  /api/auth/password  修改密码
"""
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.security import verify_password, hash_password, create_access_token
from app.utils.deps import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ---------- 请求模型 ----------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


# ---------- 路由 ----------

@router.post("/login")
def login(req: LoginRequest, request: Request, db: sqlite3.Connection = Depends(get_db)):
    """用户登录，返回 JWT"""
    user = db.execute(
        "SELECT user_id, username, password_hash FROM users WHERE username = ?",
        (req.username,),
    ).fetchone()

    client_ip = request.client.host if request.client else ""

    if not user or not verify_password(req.password, user["password_hash"]):
        log_audit(db, "login_failed", ip=client_ip,
                  target_type="user", detail={"username": req.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token({"sub": user["user_id"], "username": user["username"]})

    log_audit(db, "login", ip=client_ip,
              target_type="user", target_id=user["user_id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
    }


@router.post("/logout")
def logout(
    request: Request,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    """用户登出"""
    client_ip = request.client.host if request.client else ""
    log_audit(db, "logout", ip=client_ip,
              target_type="user", target_id=current_user["user_id"])
    return {"message": "已登出"}


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@router.put("/password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    """修改密码"""
    user = db.execute(
        "SELECT password_hash FROM users WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not verify_password(req.old_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    new_hash = hash_password(req.new_password)
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
        (new_hash, now, current_user["user_id"]),
    )

    client_ip = request.client.host if request.client else ""
    log_audit(db, "change_password", ip=client_ip,
              target_type="user", target_id=current_user["user_id"])

    return {"message": "密码修改成功"}