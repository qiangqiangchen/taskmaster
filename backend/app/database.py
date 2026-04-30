"""
数据库模块
- SQLite WAL 模式
- 全部 8 张表建表语句
- 首次启动自动创建默认管理员及系统设置
"""
import sqlite3
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import DB_PATH


def init_db():
    """初始化数据库：建表 + 默认数据"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            user_id     TEXT PRIMARY KEY,
            username    TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        -- 任务表
        CREATE TABLE IF NOT EXISTS tasks (
            task_id           TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            type              TEXT NOT NULL CHECK(type IN ('command','python_script','project','executable')),
            command_template  TEXT DEFAULT '',
            entry_config      TEXT DEFAULT '{}',
            work_dir          TEXT DEFAULT '',
            tags              TEXT DEFAULT '[]',
            enabled           INTEGER DEFAULT 1,
            daemon_config     TEXT DEFAULT '{}',
            health_check_config TEXT DEFAULT '{}',
            env_vars          TEXT DEFAULT '{}',
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );

        -- 任务参数表
        CREATE TABLE IF NOT EXISTS task_params (
            param_id   TEXT PRIMARY KEY,
            task_id    TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            mode       TEXT DEFAULT 'simple' CHECK(mode IN ('simple','advanced')),
            schema     TEXT DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        -- 调度表
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id  TEXT PRIMARY KEY,
            task_id      TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            type         TEXT NOT NULL CHECK(type IN ('cron','interval','startup')),
            cron_expr    TEXT DEFAULT '',
            interval_sec INTEGER DEFAULT 0,
            on_conflict  TEXT DEFAULT 'skip' CHECK(on_conflict IN ('skip','restart')),
            enabled      INTEGER DEFAULT 1
        );

        -- 运行实例表
        CREATE TABLE IF NOT EXISTS runs (
            run_id          TEXT PRIMARY KEY,
            task_id         TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            status          TEXT NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','running','success','failed','stopped','skipped')),
            trigger_type    TEXT NOT NULL CHECK(trigger_type IN ('manual','cron','interval','startup')),
            started_at      TEXT,
            ended_at        TEXT,
            duration_ms     INTEGER,
            exit_code       INTEGER,
            pid             INTEGER,
            final_command   TEXT DEFAULT '',
            param_snapshot  TEXT DEFAULT '{}',
            output_dir      TEXT DEFAULT '',
            log_path        TEXT DEFAULT '',
            log_size_bytes  INTEGER DEFAULT 0,
            log_truncated   INTEGER DEFAULT 0,
            failure_summary TEXT,
            intended_stop   INTEGER DEFAULT 0
        );

        -- 运行进度表（与 runs 一对一）
        CREATE TABLE IF NOT EXISTS run_progress (
            run_id     TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
            percent    INTEGER DEFAULT 0,
            current    INTEGER DEFAULT 0,
            total      INTEGER DEFAULT 0,
            eta_sec    INTEGER,
            message    TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        );

        -- 审计日志表
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id       TEXT PRIMARY KEY,
            created_at   TEXT NOT NULL,
            ip           TEXT DEFAULT '',
            action       TEXT NOT NULL,
            target_type  TEXT,
            target_id    TEXT,
            detail       TEXT DEFAULT '{}'
        );

        -- 系统设置表
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_runs_task_id ON runs(task_id);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
        CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
    """)

    # ---------- 默认管理员 ----------
    from app.utils.security import hash_password

    cursor = conn.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO users (user_id, username, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "admin", hash_password("admin"), now, now),
        )

    # ---------- 默认设置 ----------
    defaults = {
        "workspace_dir": str(DB_PATH.parent / "workspace"),
        "default_python": "python",
        "host": "127.0.0.1",
        "port": "8765",
        "lan_enabled": "false",
        "log_max_size_mb": "100",
        "retention_days": "30",
        "retention_runs": "100",
        "cleanup_time": "03:00",
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
        )

    conn.commit()
    conn.close()
    print(f"[DB] 数据库初始化完成: {DB_PATH}")


def get_db():
    """
    FastAPI 依赖注入用的数据库连接生成器
    check_same_thread=False：允许跨线程使用（FastAPI 异步调度会跨线程）
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()