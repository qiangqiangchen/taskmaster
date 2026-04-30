"""
日志路由
- 历史日志读取（分页 + 搜索）
- SSE 实时日志推送
- 日志下载
"""
import os
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from starlette.responses import Response

from app.database import get_db
from app.utils.deps import get_current_user, get_current_user_query
from app.core.run_manager import RunManager

router = APIRouter(prefix="/api/runs", tags=["日志"])


def _get_log_path(run_id: str, db) -> str | None:
    """从数据库获取日志路径"""
    row = db.execute("SELECT log_path FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return row["log_path"] if row else None


def _read_log_lines(
    log_path: str,
    search: str = "",
    offset_line: int = 0,
    limit: int = 500,
) -> dict:
    """读取日志文件，支持搜索和分页"""
    if not os.path.exists(log_path):
        return {"lines": [], "total": 0, "offset": offset_line, "has_more": False}

    all_lines = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.rstrip("\n\r")
                if search and search.lower() not in stripped.lower():
                    continue
                all_lines.append(stripped)
    except Exception:
        return {"lines": [], "total": 0, "offset": offset_line, "has_more": False}

    total = len(all_lines)
    end = min(offset_line + limit, total)
    lines = all_lines[offset_line:end]
    has_more = end < total

    return {
        "lines": lines,
        "total": total,
        "offset": offset_line,
        "has_more": has_more,
    }


# ---------- 路由 ----------

@router.get("/{run_id}/logs")
def get_logs(
    run_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    search: str = Query(""),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """读取历史日志（分页 + 搜索）— axios 请求，Header 鉴权"""
    log_path = _get_log_path(run_id, db)
    if not log_path:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    result = _read_log_lines(log_path, search, offset, limit)
    return result


@router.get("/{run_id}/logs/stream")
async def stream_logs(
    run_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user_query),
):
    """SSE 实时日志推送 — EventSource 请求，Query Token 鉴权"""
    log_path = _get_log_path(run_id, db)
    if not log_path:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    rm = RunManager.get_instance()

    async def event_generator():
        # 先发送已有日志
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    for line in lines:
                        stripped = line.rstrip("\n\r")
                        if stripped:
                            data = json.dumps({"type": "log", "line": stripped}, ensure_ascii=False)
                            yield f"data: {data}\n\n"
                            await asyncio.sleep(0)
            except Exception:
                pass

        # 如果进程仍在运行，持续推送新日志
        sent_count = 0
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    sent_count = len(lines)
            except Exception:
                pass

        max_idle = 300
        idle_time = 0
        check_interval = 0.5

        while True:
            info = rm.get_run_info(run_id)
            is_running = info is not None

            new_lines = []
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        all_lines = f.readlines()
                        if len(all_lines) > sent_count:
                            new_lines = all_lines[sent_count:]
                            sent_count = len(all_lines)
                except Exception:
                    pass

            if new_lines:
                idle_time = 0
                for line in new_lines:
                    stripped = line.rstrip("\n\r")
                    if stripped:
                        data = json.dumps({"type": "log", "line": stripped}, ensure_ascii=False)
                        yield f"data: {data}\n\n"
                await asyncio.sleep(0.1)
            else:
                idle_time += check_interval
                if not is_running:
                    if os.path.exists(log_path):
                        try:
                            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                                all_lines = f.readlines()
                                if len(all_lines) > sent_count:
                                    for line in all_lines[sent_count:]:
                                        stripped = line.rstrip("\n\r")
                                        if stripped:
                                            data = json.dumps({"type": "log", "line": stripped}, ensure_ascii=False)
                                            yield f"data: {data}\n\n"
                        except Exception:
                            pass

                    yield f"data: {json.dumps({'type': 'end'})}\n\n"
                    break

                if idle_time >= max_idle:
                    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
                    break

                await asyncio.sleep(check_interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/logs/download")
def download_log(
    run_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user_query),
):
    """下载日志文件 — window.open 请求，Query Token 鉴权"""
    log_path = _get_log_path(run_id, db)
    if not log_path:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="日志文件不存在")

    filename = f"{run_id[:8]}.log"
    return FileResponse(
        log_path,
        media_type="text/plain",
        filename=filename,
    )