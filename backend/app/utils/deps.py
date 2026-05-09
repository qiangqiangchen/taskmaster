"""
依赖项：用户认证
"""
from fastapi import Depends, HTTPException, Request, Query
from app.database import get_db


def get_current_user(
    request: Request,
    db=Depends(get_db),
):
    """通过 Header Token 获取当前用户"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证信息")

    token = auth[7:]
    user = db.execute(
        "SELECT user_id, username, role FROM users WHERE token = ?",
        (token,),
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    return {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}


def get_current_user_query(
    token: str = Query(""),
    db=Depends(get_db),
):
    """通过 Query Token 获取当前用户（用于 SSE / 下载等场景）"""
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证信息")

    user = db.execute(
        "SELECT user_id, username, role FROM users WHERE token = ?",
        (token,),
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    return {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}