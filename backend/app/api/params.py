"""
参数化系统路由
- 参数配置读取/保存
- 从命令模板自动解析占位符
- 命令渲染（Dry Run 预览）
"""
import re
import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.deps import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/tasks", tags=["参数化系统"])


# ========== 系统占位符（不作为用户参数） ==========

SYSTEM_PLACEHOLDERS = {
    "python", "script", "python_path", "script_path",
    "work_dir", "output_dir", "run_id", "task_id",
    "workspace", "progress_url", "progress_token",
}


# ========== 辅助函数 ==========

def parse_placeholders(template: str) -> list[str]:
    """从命令模板中提取 {param_name} 占位符，排除系统占位符，保持出现顺序去重"""
    all_names = re.findall(r"\{(\w+)\}", template)
    return list(dict.fromkeys(n for n in all_names if n not in SYSTEM_PLACEHOLDERS))


def generate_simple_schema(template: str) -> dict:
    """从命令模板自动生成简单模式参数 schema"""
    names = parse_placeholders(template)
    params = []
    for name in names:
        lower = name.lower()
        # 智能推断类型
        param_type = "string"
        if any(kw in lower for kw in ("count", "num", "size", "port", "timeout", "limit", "max", "min", "threads", "duration", "interval", "fail_after")):
            param_type = "number"
        elif any(kw in lower for kw in ("force", "verbose", "debug", "dry", "quiet", "yes", "no", "enable", "disable", "recursive")):
            param_type = "boolean"
        elif any(kw in lower for kw in ("dir", "output_dir", "out_dir", "dest", "target_dir")):
            param_type = "directory"
        elif any(kw in lower for kw in ("file", "input", "src", "source", "config", "template")):
            param_type = "file"
        elif any(kw in lower for kw in ("format", "mode", "type", "quality", "codec", "lang")):
            param_type = "select"

        # 智能推断默认值
        default: str | int | bool = ""
        if param_type == "number":
            default = ""
        elif param_type == "boolean":
            default = False
        elif "output" in lower or "out" in lower:
            default = "{TASK_OUTPUT_DIR}"

        # 智能推断显示名
        display_name = name.replace("_", " ").replace("-", " ").title()

        params.append({
            "name": name,
            "display_name": display_name,
            "type": param_type,
            "required": param_type not in ("boolean",),
            "default": default,
            "placeholder": "",
            "select_options": [],
            "file_scope": "",
        })

    return {"params": params}


def replace_system_placeholders(template: str, task: dict = None) -> str:
    """替换系统占位符为实际值"""
    import os
    from pathlib import Path

    result = template

    if not task:
        for ph in SYSTEM_PLACEHOLDERS:
            result = result.replace(f"{{{ph}}}", "")
        return result

    entry_config = task.get("entry_config") or {}
    if isinstance(entry_config, str):
        try:
            entry_config = json.loads(entry_config)
        except Exception:
            entry_config = {}

    python_path = entry_config.get("python_path") or "python"
    result = result.replace("{python}", python_path)
    result = result.replace("{python_path}", python_path)

    task_type = task.get("type", "")
    task_id = task.get("task_id", "")
    workspace = Path(__file__).resolve().parent.parent / "workspace"

    # 解析 {script}
    script_path = ""
    if task_type == "python_script":
        script_path = entry_config.get("script_path") or ""
        if not script_path:
            candidate = workspace / "scripts" / f"{task_id}.py"
            if candidate.exists():
                script_path = str(candidate)

    elif task_type == "project":
        project_dir = entry_config.get("project_dir") or ""
        script_filename = entry_config.get("script_filename") or "main.py"
        if project_dir:
            candidate = os.path.join(project_dir, script_filename)
            if os.path.isfile(candidate):
                script_path = candidate
            else:
                script_path = script_filename
        else:
            proj_dir = workspace / "scripts" / task_id
            if proj_dir.is_dir():
                candidate = proj_dir / script_filename
                if candidate.exists():
                    script_path = str(candidate)
                else:
                    script_path = script_filename

    elif task_type == "executable":
        script_path = entry_config.get("exe_path") or ""
        if not script_path:
            candidate = workspace / "scripts" / f"{task_id}.exe"
            if candidate.exists():
                script_path = str(candidate)

    result = result.replace("{script}", script_path)
    result = result.replace("{script_path}", script_path)

    # 清理未替换的系统占位符
    for ph in SYSTEM_PLACEHOLDERS:
        result = result.replace(f"{{{ph}}}", "")

    return result


def render_command(
    template: str,
    schema: dict,
    values: dict,
    mode: str,
    task: dict = None,
) -> tuple[str, dict]:
    """
    渲染最终命令
    返回 (final_command, env_vars_to_inject)
    """

    def _quote_if_needed(value: str) -> str:
        """如果值包含空格且未被引号包裹，自动加双引号"""
        if not value:
            return value
        if ' ' in value and not (value.startswith('"') and value.endswith('"')):
            return f'"{value}"'
        return value

    env_vars: dict[str, str] = {}

    # 先替换系统占位符
    result = replace_system_placeholders(template, task)

    params = schema.get("params", [])

    if mode == "simple":
        for p in params:
            name = p["name"]
            value = values.get(name, p.get("default", ""))
            if value is None or value == "":
                result = result.replace(f"{{{name}}}", "")
            elif isinstance(value, bool):
                result = result.replace(f"{{{name}}}", str(value).lower())
            else:
                result = result.replace(f"{{{name}}}", _quote_if_needed(str(value)))
        # 清理残留占位符
        result = re.sub(r"\{(\w+)\}", "", result)
        result = re.sub(r"\s+", " ", result).strip()
        return result, env_vars

    # 高级模式
    appended_parts: list[str] = []

    for p in params:
        name = p["name"]
        value = values.get(name, p.get("default", ""))
        concat_rule = p.get("concat_rule", "--key value")
        concat_key = p.get("concat_key", f"--{name}")

        # 环境变量注入：不拼入命令
        if concat_rule == "env_var":
            if value is not None and str(value).strip():
                env_vars[name] = str(value)
            continue

        # 如果模板中有 {name} 占位符，直接替换
        if f"{{{name}}}" in result:
            if value is None or value == "":
                result = result.replace(f"{{{name}}}", "")
            elif isinstance(value, bool):
                result = result.replace(f"{{{name}}}", str(value).lower())
            else:
                result = result.replace(f"{{{name}}}", _quote_if_needed(str(value)))
            continue

        # 否则按拼接规则追加
        str_val = str(value) if value is not None else ""

        if concat_rule == "flag":
            if value is True or str_val.lower() in ("true", "1", "yes"):
                appended_parts.append(concat_key)
        elif concat_rule == "--key value":
            if str_val.strip():
                appended_parts.append(f"{concat_key} {_quote_if_needed(str_val)}")
        elif concat_rule == "--key=value":
            if str_val.strip():
                appended_parts.append(f"{concat_key}={str_val}")
        elif concat_rule == "value_only":
            if str_val.strip():
                appended_parts.append(str_val)

    # 清理残留占位符
    result = re.sub(r"\{(\w+)\}", "", result)
    result = result.strip()

    if appended_parts:
        result = result + " " + " ".join(appended_parts)

    result = re.sub(r"\s+", " ", result).strip()
    return result, env_vars


# ========== 请求模型 ==========

class SaveParamsRequest(BaseModel):
    mode: str = Field(..., pattern=r"^(simple|advanced)$")
    schema: dict = {}


class RenderCommandRequest(BaseModel):
    values: dict = {}


# ========== 路由 ==========

@router.get("/{task_id}/params")
def get_params(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """获取任务的参数配置"""
    task = db.execute(
        "SELECT task_id, command_template FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    param = db.execute(
        "SELECT * FROM task_params WHERE task_id = ?",
        (task_id,),
    ).fetchone()

    if not param:
        # 完全没有记录：自动从模板生成
        schema = generate_simple_schema(task["command_template"])
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO task_params (param_id, task_id, mode, schema, updated_at) VALUES (?, ?, 'simple', ?, ?)",
            (str(uuid.uuid4()), task_id, json.dumps(schema, ensure_ascii=False), now),
        )
        db.commit()
        param = db.execute(
            "SELECT * FROM task_params WHERE task_id = ?",
            (task_id,),
        ).fetchone()

    result = dict(param)
    schema = json.loads(result["schema"])

    # schema 为空但模板有占位符时，自动解析并回填
    if not schema.get("params") and parse_placeholders(task["command_template"]):
        schema = generate_simple_schema(task["command_template"])
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE task_params SET schema = ?, updated_at = ? WHERE task_id = ?",
            (json.dumps(schema, ensure_ascii=False), now, task_id),
        )
        db.commit()

    result["schema"] = schema
    result["command_template"] = task["command_template"]
    return result


@router.put("/{task_id}/params")
def save_params(
    task_id: str,
    req: SaveParamsRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """保存参数配置"""
    task = db.execute(
        "SELECT task_id FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    now = datetime.now(timezone.utc).isoformat()
    existing = db.execute(
        "SELECT param_id FROM task_params WHERE task_id = ?",
        (task_id,),
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE task_params SET mode = ?, schema = ?, updated_at = ? WHERE task_id = ?",
            (req.mode, json.dumps(req.schema, ensure_ascii=False), now, task_id),
        )
    else:
        db.execute(
            "INSERT INTO task_params (param_id, task_id, mode, schema, updated_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), task_id, req.mode, json.dumps(req.schema, ensure_ascii=False), now),
        )

    log_audit(db, "update_params", target_type="task", username=_user["username"], target_id=task_id)
    return {"message": "参数配置已保存"}


@router.post("/{task_id}/parse-params")
def parse_params(
    task_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """从命令模板自动解析占位符，返回简单模式 schema"""
    task = db.execute(
        "SELECT command_template FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    schema = generate_simple_schema(task["command_template"])
    return schema


@router.post("/{task_id}/render-command")
def render_cmd(
    task_id: str,
    req: RenderCommandRequest,
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """预览最终命令（Dry Run）"""
    task = db.execute(
        "SELECT command_template, type, script_path, entry_config FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    param = db.execute(
        "SELECT mode, schema FROM task_params WHERE task_id = ?",
        (task_id,),
    ).fetchone()

    mode = param["mode"] if param else "simple"
    schema = json.loads(param["schema"]) if param else {"params": []}

    task_dict = dict(task)
    command, env_vars = render_command(
        task["command_template"], schema, req.values, mode, task_dict,
    )

    return {
        "command": command,
        "env_vars": env_vars,
    }