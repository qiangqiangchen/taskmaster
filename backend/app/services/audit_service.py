"""
审计日志服务
"""
import json
import sqlite3
from datetime import datetime, timezone


def log_audit(db, action: str, target_type: str = "", target_id: str = "",
              detail: dict | None = None, username: str = ""):
    """写入审计日志"""
    now = datetime.now(timezone.utc).isoformat()
    detail_str = json.dumps(detail or {}, ensure_ascii=False)

    db.execute(
        "INSERT INTO audit_logs (action, username, target_type, target_id, detail, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (action, username, target_type, target_id, detail_str, now),
    )