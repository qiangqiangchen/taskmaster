"""
产物管理路由
- 列出产物文件（支持子目录浏览）
- 下载产物文件
- 删除产物文件
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.database import get_db
from app.utils.deps import get_current_user, get_current_user_query

router = APIRouter(prefix="/api/runs", tags=["产物管理"])


def _get_output_dir(run_id: str, db) -> str | None:
    row = db.execute("SELECT output_dir FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return row["output_dir"] if row else None


def _safe_path(base_dir: str, relative_path: str) -> str | None:
    """防止路径穿越，确保文件在 output_dir 内"""
    base = Path(base_dir).resolve()
    target = (base / relative_path).resolve()
    try:
        target.relative_to(base)
        return str(target)
    except ValueError:
        return None


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


@router.get("/{run_id}/artifacts")
def list_artifacts(
    run_id: str,
    path: str = Query("", description="子路径，空为根目录"),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """列出产物文件"""
    row = db.execute(
        "SELECT output_dir, work_dir FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    # 优先 output_dir，其次 work_dir，最后 workspace
    base_dir = row["output_dir"]
    if not base_dir or not os.path.exists(base_dir):
        base_dir = row["work_dir"]
    if not base_dir or not os.path.exists(base_dir):
        from app.config import DATA_DIR
        base_dir = os.path.join(os.path.dirname(DATA_DIR), "workspace")
    if not base_dir or not os.path.exists(base_dir):
        return {"files": [], "current_path": "", "breadcrumbs": [], "output_dir": ""}

    target_dir = base_dir
    if path:
        safe = _safe_path(base_dir, path)
        if not safe:
            raise HTTPException(status_code=403, detail="路径不合法")
        target_dir = safe

    if not os.path.isdir(target_dir):
        return {"files": [], "current_path": "", "breadcrumbs": [], "output_dir": base_dir}

    # 面包屑
    rel = os.path.relpath(target_dir, base_dir)
    breadcrumbs = []
    if rel != ".":
        parts = rel.replace("\\", "/").split("/")
        for i, part in enumerate(parts):
            breadcrumbs.append({"name": part, "path": "/".join(parts[: i + 1])})

    # 列出文件
    files = []
    try:
        for entry in sorted(
            Path(target_dir).iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        ):
            try:
                st = entry.stat()
                is_dir = entry.is_dir()
                files.append(
                    {
                        "name": entry.name,
                        "path": str(entry.relative_to(Path(base_dir))).replace("\\", "/"),
                        "is_dir": is_dir,
                        "size": st.st_size if not is_dir else 0,
                        "size_display": _format_size(st.st_size) if not is_dir else "",
                        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        "extension": entry.suffix.lower() if not is_dir else "",
                    }
                )
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass

    return {
        "files": files,
        "current_path": path,
        "breadcrumbs": breadcrumbs,
        "output_dir": base_dir,
    }


@router.get("/{run_id}/artifacts/download")
def download_artifact(
    run_id: str,
    path: str = Query(..., description="文件相对路径"),
    db=Depends(get_db),
    _user=Depends(get_current_user_query),
):
    """下载产物文件"""
    output_dir = _get_output_dir(run_id, db)
    if not output_dir:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    safe = _safe_path(output_dir, path)
    if not safe:
        raise HTTPException(status_code=403, detail="路径不合法")

    if not os.path.isfile(safe):
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = os.path.basename(safe)
    return FileResponse(
        safe, media_type="application/octet-stream", filename=filename
    )


@router.delete("/{run_id}/artifacts")
def delete_artifact(
    run_id: str,
    path: str = Query(..., description="文件相对路径"),
    db=Depends(get_db),
    _user=Depends(get_current_user),
):
    """删除产物文件或目录"""
    output_dir = _get_output_dir(run_id, db)
    if not output_dir:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    safe = _safe_path(output_dir, path)
    if not safe:
        raise HTTPException(status_code=403, detail="路径不合法")

    if not os.path.exists(safe):
        raise HTTPException(status_code=404, detail="文件不存在")

    if os.path.isdir(safe):
        shutil.rmtree(safe)
    else:
        os.remove(safe)

    return {"message": "已删除"}