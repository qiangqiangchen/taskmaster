"""
任务管理路由
- CRUD、启用/停用、复制、脚本文件上传
"""
import os
import uuid
import json
import shutil
import zipfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

from app.config import WORKSPACE_DIR
from app.database import get_db
from app.utils.deps import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])

SCRIPTS_DIR = WORKSPACE_DIR / "scripts"


# ---------- 请求模型 ----------

class TaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern=r"^(command|python_script|project|executable)$")
    command_template: str = ""
    entry_config: dict = {}
    work_dir: str = ""
    tags: list[str] = []
    enabled: bool = True
    daemon_config: dict = {}
    health_check_config: dict = {}
    env_vars: dict = {}


class TaskUpdateRequest(BaseModel):
    name: str | None = None
    type: str | None = None
    command_template: str | None = None
    entry_config: dict | None = None
    work_dir: str | None = None
    tags: list[str] | None = None
    enabled: bool | None = None
    daemon_config: dict | None = None
    health_check_config: dict | None = None
    env_vars: dict | None = None


# ---------- 辅助函数 ----------

def _parse_task_row(row) -> dict:
    """将数据库行解析为前端友好的字典"""
    task = dict(row)
    task["tags"] = json.loads(task["tags"])
    task["entry_config"] = json.loads(task["entry_config"])
    task["daemon_config"] = json.loads(task["daemon_config"])
    task["health_check_config"] = json.loads(task["health_check_config"])
    task["env_vars"] = json.loads(task["env_vars"])
    return task


def _enrich_task(task: dict, db):
    """为任务附加运行状态和最近运行信息"""
    # 运行中数量
    running_count = db.execute(
        "SELECT COUNT(*) FROM runs WHERE task_id = ? AND status = 'running'",
        (task["task_id"],),
    ).fetchone()[0]
    if running_count > 0:
        task["run_status"] = "running"
    elif not task["enabled"]:
        task["run_status"] = "disabled"
    else:
        task["run_status"] = "idle"

    # 最近一次运行
    last_run = db.execute(
        "SELECT run_id, status, started_at, ended_at, exit_code, trigger_type "
        "FROM runs WHERE task_id = ? ORDER BY started_at DESC LIMIT 1",
        (task["task_id"],),
    ).fetchone()
    task["last_run"] = dict(last_run) if last_run else None

    # 脚本文件是否存在
    tid = task["task_id"]
    ttype = task["type"]
    has_script = False
    if ttype == "python_script":
        has_script = (SCRIPTS_DIR / f"{tid}.py").exists()
    elif ttype == "project":
        has_script = (SCRIPTS_DIR / tid).is_dir()
    elif ttype == "executable":
        has_script = (SCRIPTS_DIR / f"{tid}.exe").exists()
    elif ttype == "command":
        has_script = bool(task["command_template"].strip())
    task["has_script"] = has_script

    return task


# ---------- 路由 ----------

@router.get("")
def list_tasks(
    search: str = Query("", description="名称模糊搜索"),
    type: str | None = Query(None, description="按类型筛选"),
    status: str | None = Query(None, description="按状态: running/idle/disabled/failed"),
    tag: str | None = Query(None, description="按标签筛选"),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取任务列表"""
    conditions = []
    params: list = []

    if search:
        conditions.append("name LIKE ?")
        params.append(f"%{search}%")

    if type:
        conditions.append("type = ?")
        params.append(type)

    if tag:
        conditions.append("tags LIKE ?")
        params.append(f'%"{tag}"%')

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    rows = db.execute(
        f"SELECT * FROM tasks{where} ORDER BY updated_at DESC",
        params,
    ).fetchall()

    tasks = []
    for row in rows:
        task = _parse_task_row(row)
        task = _enrich_task(task, db)
        # 按状态二次筛选（需要 enrich 后才能判断）
        if status:
            if task["run_status"] != status:
                continue
            # failed 需检查 last_run
            if status == "failed" and (not task["last_run"] or task["last_run"]["status"] != "failed"):
                continue
        tasks.append(task)

    return {"items": tasks, "total": len(tasks)}


@router.post("")
def create_task(
    req: TaskCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """新建任务"""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """INSERT INTO tasks
           (task_id, name, type, command_template, entry_config, work_dir, tags,
            enabled, daemon_config, health_check_config, env_vars, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_id,
            req.name,
            req.type,
            req.command_template,
            json.dumps(req.entry_config, ensure_ascii=False),
            req.work_dir,
            json.dumps(req.tags, ensure_ascii=False),
            1 if req.enabled else 0,
            json.dumps(req.daemon_config, ensure_ascii=False),
            json.dumps(req.health_check_config, ensure_ascii=False),
            json.dumps(req.env_vars, ensure_ascii=False),
            now,
            now,
        ),
    )

    # 创建默认参数记录
    db.execute(
        "INSERT INTO task_params (param_id, task_id, mode, schema, updated_at) VALUES (?, ?, 'simple', '{}', ?)",
        (str(uuid.uuid4()), task_id, now),
    )

    log_audit(db, "create_task", target_type="task", target_id=task_id,
              detail={"name": req.name, "type": req.type})

    return {"task_id": task_id, "message": "任务创建成功"}


@router.get("/{task_id}")
def get_task(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取任务详情"""
    row = db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = _parse_task_row(row)
    task = _enrich_task(task, db)

    # 参数配置
    param = db.execute("SELECT * FROM task_params WHERE task_id = ?", (task_id,)).fetchone()
    task["params"] = None
    if param:
        p = dict(param)
        p["schema"] = json.loads(p["schema"])
        task["params"] = p

    # 调度配置
    schedules = db.execute("SELECT * FROM schedules WHERE task_id = ?", (task_id,)).fetchall()
    task["schedules"] = [dict(s) for s in schedules]

    # 最近 20 条运行记录
    recent_runs = db.execute(
        "SELECT run_id, status, trigger_type, started_at, ended_at, duration_ms, exit_code "
        "FROM runs WHERE task_id = ? ORDER BY started_at DESC LIMIT 20",
        (task_id,),
    ).fetchall()
    task["recent_runs"] = [dict(r) for r in recent_runs]

    return task


@router.put("/{task_id}")
def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """更新任务"""
    existing = db.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="任务不存在")

    updates = []
    params = []

    for field, value in req.model_dump(exclude_none=True).items():
        if field in ("tags", "entry_config", "daemon_config", "health_check_config", "env_vars"):
            value = json.dumps(value, ensure_ascii=False)
        if field == "enabled":
            value = 1 if value else 0
        updates.append(f"{field} = ?")
        params.append(value)

    if updates:
        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(task_id)
        db.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?", params)

    log_audit(db, "update_task", target_type="task", target_id=task_id)
    return {"message": "任务更新成功"}


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """删除任务"""
    existing = db.execute(
        "SELECT task_id, type, name FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查运行中实例
    running = db.execute(
        "SELECT COUNT(*) FROM runs WHERE task_id = ? AND status = 'running'",
        (task_id,),
    ).fetchone()[0]
    if running > 0:
        raise HTTPException(status_code=400, detail="该任务有运行中的实例，请先停止")

    # 清理脚本文件
    for p in [
        SCRIPTS_DIR / f"{task_id}.py",
        SCRIPTS_DIR / f"{task_id}.exe",
        SCRIPTS_DIR / task_id,
    ]:
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)

    db.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))

    log_audit(db, "delete_task", target_type="task", target_id=task_id,
              detail={"name": existing["name"]})
    return {"message": "任务删除成功"}


@router.post("/{task_id}/toggle")
def toggle_task(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """启用/停用切换"""
    existing = db.execute(
        "SELECT task_id, enabled, name FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="任务不存在")

    new_enabled = 0 if existing["enabled"] else 1
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE tasks SET enabled = ?, updated_at = ? WHERE task_id = ?",
        (new_enabled, now, task_id),
    )

    action = "enable_task" if new_enabled else "disable_task"
    log_audit(db, action, target_type="task", target_id=task_id,
              detail={"name": existing["name"]})

    return {"enabled": bool(new_enabled), "message": "已启用" if new_enabled else "已停用"}


@router.post("/{task_id}/copy")
def copy_task(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """复制为新任务"""
    existing = db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="源任务不存在")

    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """INSERT INTO tasks
           (task_id, name, type, command_template, entry_config, work_dir, tags,
            enabled, daemon_config, health_check_config, env_vars, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            new_id,
            existing["name"] + " (副本)",
            existing["type"],
            existing["command_template"],
            existing["entry_config"],
            existing["work_dir"],
            existing["tags"],
            1,
            existing["daemon_config"],
            existing["health_check_config"],
            existing["env_vars"],
            now,
            now,
        ),
    )

    # 复制参数配置
    param = db.execute(
        "SELECT mode, schema FROM task_params WHERE task_id = ?", (task_id,)
    ).fetchone()
    if param:
        db.execute(
            "INSERT INTO task_params (param_id, task_id, mode, schema, updated_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), new_id, param["mode"], param["schema"], now),
        )

    # 复制脚本文件
    ttype = existing["type"]
    if ttype == "python_script":
        src = SCRIPTS_DIR / f"{task_id}.py"
        if src.exists():
            shutil.copy2(src, SCRIPTS_DIR / f"{new_id}.py")
    elif ttype == "project":
        src_dir = SCRIPTS_DIR / task_id
        if src_dir.is_dir():
            shutil.copytree(src_dir, SCRIPTS_DIR / new_id)
    elif ttype == "executable":
        src = SCRIPTS_DIR / f"{task_id}.exe"
        if src.exists():
            shutil.copy2(src, SCRIPTS_DIR / f"{new_id}.exe")

    log_audit(db, "copy_task", target_type="task", target_id=new_id,
              detail={"source_task_id": task_id, "source_name": existing["name"]})

    return {"task_id": new_id, "message": "任务复制成功"}


@router.post("/{task_id}/upload")
async def upload_script(
    task_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """上传脚本文件（Python/Zip/Exe）"""
    existing = db.execute(
        "SELECT task_id, type, name FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_type = existing["type"]
    filename = file.filename or ""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    if task_type == "python_script":
        if not filename.lower().endswith(".py"):
            raise HTTPException(status_code=400, detail="Python 脚本必须上传 .py 文件")
        target = SCRIPTS_DIR / f"{task_id}.py"
        target.write_bytes(await file.read())
        config = {"script_path": str(target)}
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE tasks SET entry_config = ?, updated_at = ? WHERE task_id = ?",
            (json.dumps(config, ensure_ascii=False), now, task_id),
        )

    elif task_type == "project":
        if not filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="多文件项目必须上传 .zip 文件")
        target_dir = SCRIPTS_DIR / task_id
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True)

        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                for member in zf.namelist():
                    if member.startswith("/") or ".." in member:
                        raise HTTPException(
                            status_code=400, detail=f"压缩包包含不安全路径: {member}"
                        )
                zf.extractall(target_dir)
        finally:
            os.unlink(tmp_path)

        config = {"project_dir": str(target_dir)}
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE tasks SET entry_config = ?, updated_at = ? WHERE task_id = ?",
            (json.dumps(config, ensure_ascii=False), now, task_id),
        )

    elif task_type == "executable":
        if not filename.lower().endswith(".exe"):
            raise HTTPException(status_code=400, detail="必须上传 .exe 文件")
        target = SCRIPTS_DIR / f"{task_id}.exe"
        target.write_bytes(await file.read())
        config = {"exe_path": str(target)}
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE tasks SET entry_config = ?, updated_at = ? WHERE task_id = ?",
            (json.dumps(config, ensure_ascii=False), now, task_id),
        )

    else:
        raise HTTPException(status_code=400, detail="命令行任务不需要上传文件")

    log_audit(db, "upload_script", target_type="task", target_id=task_id,
              detail={"filename": filename, "type": task_type})

    return {"message": "文件上传成功", "filename": filename}