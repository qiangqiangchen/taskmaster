"""
健康检查路由
- 获取任务健康状态
- 手动重置健康状态
"""
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.utils.deps import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/tasks", tags=["健康检查"])


@router.get("/{task_id}/health")
def get_health(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取任务健康状态"""
    row = db.execute(
        "SELECT health_status, health_check_config FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": task_id,
        "health_status": row["health_status"] or "healthy",
        "health_check_config": row["health_check_config"] or "{}",
    }


@router.post("/{task_id}/health/reset")
def reset_health(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """手动重置健康状态为健康"""
    row = db.execute(
        "SELECT task_id FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    db.execute(
        "UPDATE tasks SET health_status = 'healthy' WHERE task_id = ?",
        (task_id,),
    )
    db.commit()

    log_audit(db, "reset_health", target_type="task", username=_user["username"], target_id=task_id)
    return {"message": "健康状态已重置"}