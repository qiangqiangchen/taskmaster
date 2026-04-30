"""
审计日志路由
- GET /api/audit/logs  分页查询审计日志
"""
import sqlite3

from fastapi import APIRouter, Depends, Query
from app.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/audit", tags=["审计日志"])


@router.get("/logs")
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    target_type: str | None = Query(None),
    db: sqlite3.Connection = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """分页查询审计日志，支持按操作类型和目标类型筛选"""
    conditions = []
    params: list = []

    if action:
        conditions.append("action = ?")
        params.append(action)
    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    total = db.execute(
        f"SELECT COUNT(*) FROM audit_logs{where}", params
    ).fetchone()[0]

    offset = (page - 1) * page_size
    rows = db.execute(
        f"SELECT * FROM audit_logs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [dict(r) for r in rows],
    }