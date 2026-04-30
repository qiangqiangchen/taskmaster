"""
运行实例路由
- 启动/停止/强制终止/重启
- 运行列表/详情
- 进度回调
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.database import get_db
from app.utils.deps import get_current_user
from app.core.run_manager import RunManager
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api", tags=["运行管理"])

rm = RunManager.get_instance()


# ---------- 请求模型 ----------

class StartRunRequest(BaseModel):
    param_values: dict = {}


class ProgressReportRequest(BaseModel):
    status: str = "running"
    percent: int = 0
    current: int = 0
    total: int = 0
    eta_sec: int | None = None
    message: str = ""


# ---------- 路由 ----------

@router.post("/tasks/{task_id}/run")
def start_run(
    task_id: str,
    req: StartRunRequest | None = None,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """启动一次运行"""
    req = req or StartRunRequest()
    try:
        run_id = rm.start_run(task_id, "manual", req.param_values)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {e}")

    log_audit(db, "start_run", target_type="run", target_id=run_id,
              detail={"task_id": task_id})
    return {"run_id": run_id, "message": "运行已启动"}


@router.post("/runs/{run_id}/stop")
def stop_run(
    run_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """优雅停止运行"""
    if not rm.is_running(run_id):
        raise HTTPException(status_code=400, detail="该运行不在执行中")

    ok = rm.stop_run(run_id)
    if not ok:
        raise HTTPException(status_code=500, detail="停止失败")

    log_audit(db, "stop_run", target_type="run", target_id=run_id)
    return {"message": "停止指令已发送"}


@router.post("/runs/{run_id}/kill")
def force_kill_run(
    run_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """强制终止运行"""
    if not rm.is_running(run_id):
        raise HTTPException(status_code=400, detail="该运行不在执行中")

    ok = rm.force_kill_run(run_id)
    if not ok:
        raise HTTPException(status_code=500, detail="终止失败")

    log_audit(db, "force_kill_run", target_type="run", target_id=run_id)
    return {"message": "已强制终止"}


@router.post("/runs/{run_id}/restart")
def restart_run(
    run_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """重启运行（停止旧的，用相同参数启动新的）"""
    row = db.execute(
        "SELECT task_id, param_snapshot, status FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    task_id = row["task_id"]
    param_snapshot = json.loads(row["param_snapshot"] or "{}")

    # 如果还在运行，先停止
    if row["status"] == "running" and rm.is_running(run_id):
        rm.stop_run(run_id)

    try:
        new_run_id = rm.start_run(task_id, "manual", param_snapshot)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启失败: {e}")

    log_audit(db, "restart_run", target_type="run", target_id=new_run_id,
              detail={"old_run_id": run_id})
    return {"run_id": new_run_id, "message": "已重启"}


@router.get("/runs")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_id: str | None = Query(None),
    status: str | None = Query(None),
    trigger_type: str | None = Query(None),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """分页查询运行列表"""
    conditions = []
    params: list = []

    if task_id:
        conditions.append("r.task_id = ?")
        params.append(task_id)
    if status:
        conditions.append("r.status = ?")
        params.append(status)
    if trigger_type:
        conditions.append("r.trigger_type = ?")
        params.append(trigger_type)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    total = db.execute(
        f"SELECT COUNT(*) FROM runs r{where}", params
    ).fetchone()[0]

    offset = (page - 1) * page_size
    rows = db.execute(
        f"SELECT r.*, t.name as task_name, t.type as task_type "
        f"FROM runs r LEFT JOIN tasks t ON r.task_id = t.task_id "
        f"{where} ORDER BY r.started_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    items = []
    for row in rows:
        r = dict(row)
        r["param_snapshot"] = json.loads(r["param_snapshot"] or "{}")
        r["failure_summary"] = json.loads(r["failure_summary"]) if r["failure_summary"] else None
        items.append(r)

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取运行详情"""
    row = db.execute(
        "SELECT r.*, t.name as task_name, t.type as task_type "
        "FROM runs r LEFT JOIN tasks t ON r.task_id = t.task_id "
        "WHERE r.run_id = ?",
        (run_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    result = dict(row)
    result["param_snapshot"] = json.loads(result["param_snapshot"] or "{}")
    result["failure_summary"] = (
        json.loads(result["failure_summary"]) if result["failure_summary"] else None
    )

    # 进度
    progress = db.execute(
        "SELECT * FROM run_progress WHERE run_id = ?", (run_id,)
    ).fetchone()
    result["progress"] = dict(progress) if progress else None

    # 是否仍在内存中（真正运行中）
    result["is_active"] = rm.is_running(run_id)

    return result


@router.post("/runs/{run_id}/progress")
def report_progress(
    run_id: str,
    req: ProgressReportRequest,
    request: Request,
):
    """脚本进度回调（由子进程调用，校验 token）"""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="缺少进度回调 Token")

    ok = rm.update_progress(run_id, token, req.model_dump())
    if not ok:
        raise HTTPException(status_code=403, detail="Token 无效或运行已结束")

    return {"message": "进度已更新"}