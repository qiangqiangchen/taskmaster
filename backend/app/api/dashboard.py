"""
仪表盘路由
"""
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/stats")
def get_dashboard_stats(
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """仪表盘统计"""
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    enabled_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE enabled = 1").fetchone()[0]
    total_runs = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    running_runs = db.execute("SELECT COUNT(*) FROM runs WHERE status = 'running'").fetchone()[0]
    success_runs = db.execute("SELECT COUNT(*) FROM runs WHERE status = 'success'").fetchone()[0]
    failed_runs = db.execute("SELECT COUNT(*) FROM runs WHERE status = 'failed'").fetchone()[0]
    failed_24h = db.execute(
        "SELECT COUNT(*) FROM runs WHERE status = 'failed' AND ended_at > datetime('now', '-1 day')"
    ).fetchone()[0]

    success_rate = 0
    if (success_runs + failed_runs) > 0:
        success_rate = round(success_runs / (success_runs + failed_runs) * 100, 1)

    return {
        "total_tasks": total_tasks,
        "enabled_tasks": enabled_tasks,
        "total_runs": total_runs,
        "running_runs": running_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "failed_24h": failed_24h,
        "success_rate": success_rate,
    }


@router.get("/recent-runs")
def get_recent_runs(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """最近运行记录"""
    rows = db.execute(
        "SELECT run_id, task_id, task_name, status, trigger_type, "
        "started_at, ended_at, duration_ms, exit_code "
        "FROM runs ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return {"items": [dict(r) for r in rows]}