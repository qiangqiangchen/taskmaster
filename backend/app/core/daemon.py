"""
守护进程管理器
- 监控运行失败的实例
- 根据守护配置自动重启
- 跟踪重启次数，防止无限重启
"""
import json
import threading
import sqlite3
from datetime import datetime, timezone, timedelta

from app.database import DB_PATH
from app.core.run_manager import RunManager


class DaemonManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._thread = None
        self._running = False
        self._reload_event = threading.Event()

    @classmethod
    def get_instance(cls) -> "DaemonManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[DaemonManager] 守护管理器已启动")

    def stop(self):
        self._running = False
        self._reload_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[DaemonManager] 守护管理器已停止")

    def reload(self):
        print("[DaemonManager] 收到重载信号")
        self._reload_event.set()

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"[DaemonManager] tick 异常: {e}")

            self._reload_event.clear()
            self._reload_event.wait(timeout=10)

    def _tick(self):
        conn = self._get_conn()
        try:
            now = datetime.now(timezone.utc)

            # === 第一步：重置窗口过期后的 checked 标记 ===
            checked_tasks = conn.execute(
                "SELECT DISTINCT task_id FROM runs "
                "WHERE daemon_checked = 1 AND status = 'failed' AND intended_stop = 0"
            ).fetchall()

            for ct in checked_tasks:
                tid = ct["task_id"]
                task_row = conn.execute(
                    "SELECT daemon_config FROM tasks WHERE task_id = ?", (tid,)
                ).fetchone()
                if not task_row:
                    continue
                dc = json.loads(task_row["daemon_config"] or "{}")
                if not dc.get("auto_restart"):
                    continue
                reset_time = dc.get("reset_time", 600)
                window_start = (now - timedelta(seconds=reset_time)).isoformat()
                restart_count = conn.execute(
                    "SELECT COUNT(*) FROM runs "
                    "WHERE task_id = ? AND trigger_type = 'daemon_restart' "
                    "AND started_at > ?",
                    (tid, window_start),
                ).fetchone()[0]
                # 窗口内无重启记录，说明窗口已过期，重置 checked
                if restart_count == 0:
                    conn.execute(
                        "UPDATE runs SET daemon_checked = 0 "
                        "WHERE task_id = ? AND daemon_checked = 1 "
                        "AND status = 'failed' AND intended_stop = 0",
                        (tid,),
                    )
                    print(f"[DaemonManager] {tid[:8]}: 重置窗口已过期，重新启用检查")

            # === 第二步：检查失败的 run ===
            cutoff = (now - timedelta(minutes=5)).isoformat()
            failed_runs = conn.execute(
                "SELECT r.*, t.daemon_config, t.name as task_name, t.enabled as task_enabled "
                "FROM runs r JOIN tasks t ON r.task_id = t.task_id "
                "WHERE r.status = 'failed' "
                "AND r.intended_stop = 0 "
                "AND r.trigger_type NOT IN ('skipped') "
                "AND r.ended_at > ? "
                "AND COALESCE(r.daemon_checked, 0) = 0",
                (cutoff,),
            ).fetchall()

            for run_row in failed_runs:
                task_id = run_row["task_id"]
                run_id = run_row["run_id"]
                task_name = run_row["task_name"]

                if not run_row["task_enabled"]:
                    conn.execute(
                        "UPDATE runs SET daemon_checked = 1 WHERE run_id = ?",
                        (run_id,),
                    )
                    continue

                daemon_config = json.loads(run_row["daemon_config"] or "{}")
                auto_restart = daemon_config.get("auto_restart", False)

                if not auto_restart:
                    conn.execute(
                        "UPDATE runs SET daemon_checked = 1 WHERE run_id = ?",
                        (run_id,),
                    )
                    continue

                max_restarts = daemon_config.get("max_restarts", 5)
                reset_time = daemon_config.get("reset_time", 600)

                window_start = (
                        now - timedelta(seconds=reset_time)
                ).isoformat()
                restart_count = conn.execute(
                    "SELECT COUNT(*) FROM runs "
                    "WHERE task_id = ? AND trigger_type = 'daemon_restart' "
                    "AND started_at > ?",
                    (task_id, window_start),
                ).fetchone()[0]

                if restart_count >= max_restarts:
                    # 达到上限，不标记 checked，等窗口过期后重新检查
                    print(
                        f"[DaemonManager] {task_name}: 已达最大重启次数 "
                        f"{restart_count}/{max_restarts}，等待窗口过期"
                    )
                    continue

                # 标记已检查
                conn.execute(
                    "UPDATE runs SET daemon_checked = 1 WHERE run_id = ?",
                    (run_id,),
                )

                # 检查是否已有运行中实例
                running = conn.execute(
                    "SELECT run_id FROM runs WHERE task_id = ? AND status = 'running'",
                    (task_id,),
                ).fetchone()

                if running:
                    print(f"[DaemonManager] {task_name}: 已有运行中实例，跳过重启")
                    continue

                # 先提交标记
                try:
                    conn.commit()
                except Exception:
                    pass

                # 执行重启
                try:
                    rm = RunManager.get_instance()
                    param_snapshot = json.loads(run_row["param_snapshot"] or "{}")
                    new_run_id = rm.start_run(
                        task_id, "daemon_restart", param_snapshot
                    )
                    print(
                        f"[DaemonManager] {task_name}: 自动重启 "
                        f"run={new_run_id[:8]}... "
                        f"({restart_count + 1}/{max_restarts})"
                    )
                except Exception as e:
                    print(f"[DaemonManager] {task_name}: 自动重启失败 - {e}")

            try:
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn