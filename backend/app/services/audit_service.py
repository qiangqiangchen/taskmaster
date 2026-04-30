"""
审计日志服务
- 写入审计记录
"""
import uuid
import json
from datetime import datetime, timezone

import sqlite3


def log_audit(
    db: sqlite3.Connection,
    action: str,
    ip: str = "",
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
):
    """写入一条审计日志"""
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO audit_logs (log_id, created_at, ip, action, target_type, target_id, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            now,
            ip,
            action,
            target_type,
            target_id,
            json.dumps(detail or {}, ensure_ascii=False),
        ),
    )
    db.commit()