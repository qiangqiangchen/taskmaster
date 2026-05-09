"""
数据库维护路由
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta

from app.database import get_db, DB_PATH
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/maintenance", tags=["维护"])


@router.get("/db-size")
def get_db_size(
    _user=Depends(get_current_user),
):
    """获取数据库文件大小"""
    import os
    size_bytes = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    return {"size_bytes": size_bytes, "size_human": size_str}


@router.post("/clean-logs")
def clean_old_logs(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """清理指定天数之前的运行日志文件"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    runs = db.execute(
        "SELECT run_id, log_path FROM runs WHERE ended_at < ? AND log_path IS NOT NULL",
        (cutoff,),
    ).fetchall()

    import os
    cleaned = 0
    freed_bytes = 0
    for run in runs:
        log_path = run["log_path"]
        if log_path and os.path.isfile(log_path):
            freed_bytes += os.path.getsize(log_path)
            try:
                os.remove(log_path)
                cleaned += 1
            except Exception:
                pass

    return {
        "cleaned": cleaned,
        "freed_bytes": freed_bytes,
        "freed_human": f"{freed_bytes / (1024*1024):.1f} MB" if freed_bytes >= 1024*1024 else f"{freed_bytes / 1024:.1f} KB",
    }


@router.post("/clean-runs")
def clean_old_runs(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """清理指定天数之前的运行记录"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = db.execute(
        "DELETE FROM runs WHERE ended_at < ? AND status != 'running'",
        (cutoff,),
    )
    db.commit()
    return {"deleted": result.rowcount}


@router.post("/clean-audit")
def clean_old_audit(
    days: int = Query(90, ge=1, le=365),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """清理指定天数之前的审计日志"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = db.execute(
        "DELETE FROM audit_logs WHERE created_at < ?",
        (cutoff,),
    )
    db.commit()
    return {"deleted": result.rowcount}


@router.post("/vacuum")
def vacuum_db(
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """压缩数据库"""
    db.execute("VACUUM")
    return {"message": "数据库压缩完成"}