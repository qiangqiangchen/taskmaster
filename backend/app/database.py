"""
数据库模块
- SQLite WAL 模式
- 全部 8 张表建表语句
- 首次启动自动创建默认管理员及系统设置
"""
import sqlite3
import uuid
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import DB_PATH,DATA_DIR



def init_db():
    """初始化数据库，创建所有表"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    # ============ 建表 ============

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            token TEXT,
            last_login TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'command',
            command_template TEXT DEFAULT '',
            entry_config TEXT DEFAULT '{}',
            has_script INTEGER DEFAULT 0,
            script_path TEXT,
            work_dir TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            enabled INTEGER DEFAULT 1,
            daemon_config TEXT DEFAULT '{}',
            health_check_config TEXT DEFAULT '{}',
            schedule_config TEXT DEFAULT '{}',
            env_vars TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_params (
            param_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT '',
            display_name TEXT DEFAULT '',
            param_type TEXT DEFAULT 'text',
            mode TEXT DEFAULT 'simple',
            default_value TEXT DEFAULT '',
            choices TEXT DEFAULT '[]',
            required INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            schema TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id TEXT,
                task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                type TEXT DEFAULT 'cron',
                schedule_type TEXT DEFAULT 'cron',
                cron_expr TEXT DEFAULT '',
                interval_sec INTEGER DEFAULT 0,
                interval_seconds INTEGER DEFAULT 0,
                on_conflict TEXT DEFAULT 'skip',
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                last_run_at TEXT,
                next_run TEXT,
                next_run_at TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            task_name TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            trigger_type TEXT NOT NULL DEFAULT 'manual',
            command_template TEXT,
            final_command TEXT DEFAULT '',
            work_dir TEXT,
            param_snapshot TEXT DEFAULT '{}',
            env_vars TEXT DEFAULT '{}',
            pid INTEGER,
            exit_code INTEGER,
            log_path TEXT DEFAULT '',
            log_size_bytes INTEGER DEFAULT 0,
            log_truncated INTEGER DEFAULT 0,
            output_dir TEXT DEFAULT '',
            progress TEXT DEFAULT '{}',
            failure_summary TEXT,
            started_at TEXT,
            ended_at TEXT,
            duration_ms INTEGER,
            intended_stop INTEGER DEFAULT 0,
            daemon_checked INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_progress (
            run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
            percent INTEGER DEFAULT 0,
            current INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            eta_sec INTEGER,
            message TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id TEXT,
            action TEXT NOT NULL,
            username TEXT DEFAULT '',
            ip TEXT DEFAULT '',
            target_type TEXT DEFAULT '',
            target_id TEXT DEFAULT '',
            detail TEXT DEFAULT '{}',
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)

    # ============ 索引 ============

    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_task_id ON runs(task_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")

    # ============ 迁移（已注释，删库重建时不需要） ============
    # 如需在旧库上增量升级，取消以下注释即可：
    #
    # migrations = [
    #     ("ALTER TABLE tasks ADD COLUMN entry_config TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE tasks ADD COLUMN has_script INTEGER DEFAULT 0",),
    #     ("ALTER TABLE tasks ADD COLUMN script_path TEXT",),
    #     ("ALTER TABLE tasks ADD COLUMN daemon_config TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE tasks ADD COLUMN health_check_config TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE tasks ADD COLUMN schedule_config TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE tasks ADD COLUMN env_vars TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE tasks ADD COLUMN updated_at TEXT",),
    #     ("ALTER TABLE runs ADD COLUMN task_name TEXT",),
    #     ("ALTER TABLE runs ADD COLUMN log_size_bytes INTEGER DEFAULT 0",),
    #     ("ALTER TABLE runs ADD COLUMN log_truncated INTEGER DEFAULT 0",),
    #     ("ALTER TABLE runs ADD COLUMN progress TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE runs ADD COLUMN failure_summary TEXT",),
    #     ("ALTER TABLE runs ADD COLUMN intended_stop INTEGER DEFAULT 0",),
    #     ("ALTER TABLE runs ADD COLUMN daemon_checked INTEGER DEFAULT 0",),
    #     ("ALTER TABLE runs ADD COLUMN env_vars TEXT DEFAULT '{}'",),
    #     ("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'admin'",),
    #     ("ALTER TABLE users ADD COLUMN token TEXT",),
    #     ("ALTER TABLE users ADD COLUMN last_login TEXT",),
    #     ("ALTER TABLE audit_logs ADD COLUMN username TEXT DEFAULT ''",),
    # ]
    # for (sql,) in migrations:
    #     try:
    #         conn.execute(sql)
    #     except Exception:
    #         pass

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
