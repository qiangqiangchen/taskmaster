"""
认证路由
"""
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.database import get_db
from app.utils.deps import get_current_user
from app.services.audit_service import log_audit
from app.config import SECRET_KEY

router = APIRouter(prefix="/api", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{password}{SECRET_KEY}".encode()).hexdigest()


def init_default_user(db):
    """初始化默认管理员账号"""
    existing = db.execute("SELECT user_id FROM users WHERE username = 'admin'").fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if not existing:
        db.execute(
            "INSERT INTO users (user_id, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (secrets.token_hex(8), "admin", hash_password("admin123"), "admin", now),
        )
        db.commit()
        print("[TaskMaster] 已创建默认管理员账号 admin/admin123")
    else:
        # 确保 admin 密码正确
        db.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (hash_password("admin123"),),
        )
        db.commit()


@router.post("/auth/login")
def login(
    req: LoginRequest,
    request: Request,
    db=Depends(get_db),
):
    """用户登录"""
    init_default_user(db)

    username = req.username
    password = req.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="请输入用户名和密码")

    user = db.execute(
        "SELECT user_id, username, password_hash, role FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if not user or user["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 token
    token = secrets.token_hex(32)
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        "UPDATE users SET token = ?, last_login = ? WHERE user_id = ?",
        (token, now, user["user_id"]),
    )
    db.commit()

    # 审计日志
    client_ip = request.client.host if request.client else "unknown"
    log_audit(db, "login", target_type="user", target_id=username,
              username=username, detail={"ip": client_ip})

    return {"token": token, "username": username, "role": user["role"]}


@router.post("/auth/change-password")
def change_password(
    req: ChangePasswordRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """修改密码"""
    old_password = req.old_password
    new_password = req.new_password

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="请输入旧密码和新密码")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于6位")

    user = db.execute(
        "SELECT user_id, password_hash FROM users WHERE username = ?",
        (_user["username"],),
    ).fetchone()

    if not user or user["password_hash"] != hash_password(old_password):
        raise HTTPException(status_code=400, detail="旧密码错误")

    db.execute(
        "UPDATE users SET password_hash = ? WHERE user_id = ?",
        (hash_password(new_password), user["user_id"]),
    )
    db.commit()

    log_audit(db, "change_password", target_type="user",
              target_id=_user["username"], username=_user["username"])

    return {"message": "密码修改成功"}