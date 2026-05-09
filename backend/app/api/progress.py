"""
进度上报路由
- 供脚本通过 HTTP 上报进度（SDK / 内联方式）
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.core.run_manager import RunManager

router = APIRouter(prefix="/api/runs", tags=["进度"])


class ProgressPayload(BaseModel):
    percent: int = 0
    current: Optional[int] = None
    total: Optional[int] = None
    eta_sec: Optional[float] = None
    message: str = ""
    status: str = "running"


@router.post("/{run_id}/progress")
def report_progress(
    run_id: str,
    payload: ProgressPayload,
    request: Request,
):
    """脚本上报进度，支持 Header 或 Query 两种 token 方式"""
    # 优先从 Header 取，其次从 Query 取
    token = ""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.query_params.get("token", "")

    if not token:
        print(f"[Progress] 缺少 token, run={run_id[:8]}")
        raise HTTPException(status_code=400, detail="缺少 token")

    rm = RunManager.get_instance()

    # 更新内存中的进度（供 SSE 推送）
    info = rm.get_run_info(run_id)
    if info and info.progress_token == token:
        info.progress = payload.model_dump()
        print(f"[Progress] 内存已更新, run={run_id[:8]} percent={payload.percent}%")
    else:
        print(f"[Progress] token 不匹配或运行不存在, run={run_id[:8]} has_info={info is not None}")

    # 写入数据库
    ok = rm.update_progress(run_id, token, payload.model_dump())
    if not ok:
        print(f"[Progress] 数据库写入失败, run={run_id[:8]}")
        raise HTTPException(status_code=403, detail="token 无效或运行不存在")

    return {"ok": True}