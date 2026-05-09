"""
全局设置路由
"""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.deps import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api", tags=["系统设置"])


# 默认设置
DEFAULTS = {
    "log_max_size_mb": "100",
    "max_concurrent_runs": "10",
    "default_stop_timeout": "5",
    "daemon_check_interval": "10",
}


@router.get("/settings")
def get_settings(
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取所有设置"""
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    settings = {}
    for row in rows:
        settings[row["key"]] = row["value"]

    # 填充默认值
    for key, default in DEFAULTS.items():
        if key not in settings:
            settings[key] = default

    return settings


class UpdateSettingsRequest(BaseModel):
    settings: dict


@router.put("/settings")
def update_settings(
    req: UpdateSettingsRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """更新设置"""
    for key, value in req.settings.items():
        # 只允许更新已知键
        if key in DEFAULTS:
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    db.commit()
    log_audit(db, "update_settings", target_type="system", target_id="global", username=_user["username"])
    return {"message": "设置已保存"}


@router.get("/settings/stats")
def get_system_stats(
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取系统统计"""
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    enabled_tasks = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE enabled = 1"
    ).fetchone()[0]
    total_runs = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    running_runs = db.execute(
        "SELECT COUNT(*) FROM runs WHERE status = 'running'"
    ).fetchone()[0]
    failed_runs_24h = db.execute(
        "SELECT COUNT(*) FROM runs WHERE status = 'failed' AND ended_at > datetime('now', '-1 day')"
    ).fetchone()[0]

    return {
        "total_tasks": total_tasks,
        "enabled_tasks": enabled_tasks,
        "total_runs": total_runs,
        "running_runs": running_runs,
        "failed_runs_24h": failed_runs_24h,
    }