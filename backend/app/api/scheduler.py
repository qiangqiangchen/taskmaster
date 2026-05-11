"""
调度配置路由
- 获取/保存调度配置
- 校验 cron 表达式
- 手动重载调度器
"""
import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.deps import get_current_user
from app.core.cron import validate_cron, next_run, CRON_PRESETS
from app.core.scheduler import Scheduler
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/tasks", tags=["定时调度"])


class SaveScheduleRequest(BaseModel):
    enabled: bool = False
    schedule_type: str = Field(..., pattern=r"^(cron|interval)$")
    cron_expression: str = ""
    interval_seconds: int = Field(0, ge=0)


@router.get("/{task_id}/schedule")
def get_schedule(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取任务的调度配置"""
    task = db.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    sch = db.execute(
        "SELECT * FROM schedules WHERE task_id = ?", (task_id,)
    ).fetchone()

    if not sch:
        return {
            "task_id": task_id,
            "enabled": False,
            "schedule_type": "cron",
            "cron_expression": "",
            "interval_seconds": 0,
            "next_run_at": None,
            "last_run_at": None,
        }

    result = dict(sch)
    result["enabled"] = bool(result["enabled"])

    # 计算下次执行时间的可读格式
    if result["schedule_type"] == "cron" and result["cron_expression"]:
        try:
            nr = next_run(result["cron_expression"])
            result["next_run_readable"] = nr.strftime("%Y-%m-%d %H:%M") if nr else None
        except Exception:
            result["next_run_readable"] = None
    else:
        result["next_run_readable"] = None

    return result


@router.put("/{task_id}/schedule")
def save_schedule(
    task_id: str,
    req: SaveScheduleRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """保存调度配置"""
    task = db.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 校验 cron 表达式
    if req.schedule_type == "cron" and req.enabled:
        if not req.cron_expression.strip():
            raise HTTPException(status_code=400, detail="cron 表达式不能为空")
        ok, err = validate_cron(req.cron_expression)
        if not ok:
            raise HTTPException(status_code=400, detail=f"cron 表达式无效: {err}")

    # 校验 interval
    if req.schedule_type == "interval" and req.enabled:
        if req.interval_seconds < 10:
            raise HTTPException(status_code=400, detail="间隔不能小于 10 秒")

    # 计算下次执行时间
    next_run_at = None
    if req.enabled:
        from app.core.scheduler import Scheduler
        sch_row = db.execute("SELECT * FROM schedules WHERE task_id = ?", (task_id,)).fetchone()
        sch_dict = dict(sch_row) if sch_row else {}
        sch_dict["schedule_type"] = req.schedule_type
        sch_dict["cron_expression"] = req.cron_expression
        sch_dict["interval_seconds"] = req.interval_seconds

        if req.schedule_type == "cron":
            try:
                nr = next_run(req.cron_expression)
                if nr:
                    next_run_at = nr.isoformat()
            except Exception:
                pass
        elif req.schedule_type == "interval":
            from datetime import timedelta
            next_run_at = (datetime.now(timezone.utc) + timedelta(seconds=req.interval_seconds)).isoformat()

    now = datetime.now(timezone.utc).isoformat()
    existing = db.execute(
        "SELECT schedule_id FROM schedules WHERE task_id = ?", (task_id,)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE schedules SET enabled = ?, schedule_type = ?, cron_expression = ?, "
            "interval_seconds = ?, next_run_at = ?, updated_at = ? WHERE task_id = ?",
            (
                1 if req.enabled else 0,
                req.schedule_type,
                req.cron_expression,
                req.interval_seconds,
                next_run_at,
                now,
                task_id,
            ),
        )
    else:
        db.execute(
            "INSERT INTO schedules (schedule_id, task_id, enabled, schedule_type, "
            "cron_expression, interval_seconds, next_run_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                task_id,
                1 if req.enabled else 0,
                req.schedule_type,
                req.cron_expression,
                req.interval_seconds,
                next_run_at,
                now,
                now,
            ),
        )

    db.commit()

    # 通知调度器重载
    Scheduler.get_instance().reload()

    log_audit(db, "update_schedule", target_type="task", username=_user["username"], target_id=task_id)
    return {"message": "调度配置已保存", "next_run_at": next_run_at}


@router.post("/{task_id}/schedule/validate-cron")
def validate_cron_expr(
    task_id: str,
    body: dict = None,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """校验 cron 表达式并返回下次执行时间"""
    body = body or {}
    expr = body.get("expression", "")
    ok, err = validate_cron(expr)
    nr = None
    nr_readable = None
    if ok:
        result = next_run(expr)
        if result:
            nr = result.isoformat()
            nr_readable = result.strftime("%Y-%m-%d %H:%M:%S")

    return {"valid": ok, "error": err, "next_run": nr, "next_run_readable": nr_readable}


@router.get("/scheduler/presets")
def get_cron_presets(
    _user=Depends(get_current_user),
):
    """获取 cron 预设列表"""
    presets = []
    for name, expr in CRON_PRESETS.items():
        nr = None
        try:
            result = next_run(expr)
            if result:
                nr = result.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        presets.append({"name": name, "expression": expr, "next_run": nr})
    return {"presets": presets}