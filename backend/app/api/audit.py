from fastapi import APIRouter, Depends, Query
from app.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["审计日志"])


@router.get("/audit")
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str = Query(""),
    username: str = Query(""),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取审计日志"""
    conditions = []
    params = []

    if action:
        conditions.append("action = ?")
        params.append(action)
    if username:
        conditions.append("username = ?")
        params.append(username)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    total = db.execute(
        f"SELECT COUNT(*) FROM audit_logs {where}", params
    ).fetchone()[0]

    offset = (page - 1) * page_size
    rows = db.execute(
        f"SELECT * FROM audit_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    items = [dict(row) for row in rows]

    return {"items": items, "total": total, "page": page, "page_size": page_size}