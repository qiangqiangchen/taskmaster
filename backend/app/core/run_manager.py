"""
运行管理器 - 进程调度与守护核心模块
- 进程启停（Job Object 隔离）
- 日志采集（带时间戳注入、大小截断）
- 进程退出检测与状态同步
- 孤儿运行恢复
"""
import os
import subprocess
import threading
import uuid
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

import sqlite3

from app.config import WORKSPACE_DIR
from app.database import DB_PATH
from app.core.job_object import (
    create_job_object,
    assign_process_to_job,
    close_job_object,
)


class RunInfo:
    """运行实例的内存状态"""
    __slots__ = [
        "run_id", "task_id", "process", "job_handle",
        "log_file", "log_path", "output_dir", "progress_token",
        "monitor_thread", "log_size", "log_truncated",
    ]

    def __init__(self):
        self.run_id = ""
        self.task_id = ""
        self.process: subprocess.Popen | None = None
        self.job_handle: int = 0
        self.log_file = None
        self.log_path: str = ""
        self.output_dir: str = ""
        self.progress_token: str = ""
        self.monitor_thread: threading.Thread | None = None
        self.log_size: int = 0
        self.log_truncated: bool = False


class RunManager:
    """进程管理单例"""

    _instance = None
    _init_lock = threading.Lock()

    def __init__(self):
        self.active_runs: dict[str, RunInfo] = {}
        self._runs_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "RunManager":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ========== 启动运行 ==========

    def start_run(
        self,
        task_id: str,
        trigger_type: str = "manual",
        param_values: dict | None = None,
    ) -> str:
        """启动一次运行，返回 run_id"""
        conn = self._get_conn()
        try:
            task = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not task:
                raise ValueError("任务不存在")
            if not task["enabled"]:
                raise ValueError("任务已停用，请先启用")

            # ---- 冲突策略 ----
            running = conn.execute(
                "SELECT run_id FROM runs WHERE task_id = ? AND status = 'running'",
                (task_id,),
            ).fetchone()

            if running:
                daemon_cfg = json.loads(task["daemon_config"] or "{}")
                if trigger_type == "manual":
                    strategy = daemon_cfg.get("manual_conflict", "restart")
                    if strategy == "reject":
                        raise ValueError("该任务正在运行，请先停止")
                    # restart: 先停旧的
                    self.stop_run(running["run_id"])
                else:
                    strategy = daemon_cfg.get("auto_conflict", "skip")
                    if strategy == "skip":
                        run_id = str(uuid.uuid4())
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            "INSERT INTO runs (run_id, task_id, status, trigger_type, started_at, ended_at, final_command) "
                            "VALUES (?, ?, 'skipped', ?, ?, ?, '')",
                            (run_id, task_id, trigger_type, now, now),
                        )
                        conn.commit()
                        return run_id
                    else:
                        self.stop_run(running["run_id"])

            # ---- 渲染命令 ----
            from app.api.params import render_command

            param_row = conn.execute(
                "SELECT mode, schema FROM task_params WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            mode = param_row["mode"] if param_row else "simple"
            schema = json.loads(param_row["schema"]) if param_row else {"params": []}
            values = param_values or {}

            command, env_vars = render_command(
                task["command_template"], schema, values, mode
            )
            if not command.strip():
                raise ValueError("渲染后的命令为空，请检查命令模板和参数")

            # ---- 创建 run 记录 ----
            run_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            progress_token = secrets.token_urlsafe(32)

            output_dir = WORKSPACE_DIR / "outputs" / task_id / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            log_dir = WORKSPACE_DIR / "logs" / task_id
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = str(log_dir / f"{run_id}.log")

            # ---- 构建环境变量 ----
            env = os.environ.copy()
            env["TASK_RUN_ID"] = run_id
            env["TASK_OUTPUT_DIR"] = str(output_dir)
            env["TASK_WORKSPACE"] = str(WORKSPACE_DIR)
            env["TASK_PROGRESS_URL"] = (
                f"http://127.0.0.1:8765/api/runs/{run_id}/progress"
            )
            env["TASK_PROGRESS_TOKEN"] = progress_token

            # 用户自定义环境变量（不覆盖平台变量）
            for k, v in json.loads(task["env_vars"] or "{}").items():
                if k not in env:
                    env[k] = str(v)
            # 渲染产生的环境变量
            for k, v in env_vars.items():
                if k not in env:
                    env[k] = str(v)

            # ---- 工作目录 ----
            work_dir = task["work_dir"] or str(WORKSPACE_DIR)

            # ---- 日志大小限制 ----
            log_max_mb = 100
            try:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = 'log_max_size_mb'"
                ).fetchone()
                if row:
                    log_max_mb = int(row["value"])
            except Exception:
                pass
            log_max_bytes = log_max_mb * 1024 * 1024

            # ---- 停止超时 ----
            daemon_cfg = json.loads(task["daemon_config"] or "{}")
            stop_timeout = daemon_cfg.get("stop_timeout", 5)

            # ---- 创建 Job Object ----
            job_handle = create_job_object()

            # ---- 进程启动标志 ----
            entry_cfg = json.loads(task["entry_config"] or "{}")
            creation_flags = 0
            if task["type"] == "executable" and entry_cfg.get("no_window"):
                creation_flags = 0x08000000  # CREATE_NO_WINDOW

            # ---- 启动子进程 ----
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=work_dir,
                creationflags=creation_flags,
                shell=True,
            )

            # ---- 分配到 Job Object ----
            assign_process_to_job(job_handle, process.pid)

            # ---- 构建 RunInfo ----
            info = RunInfo()
            info.run_id = run_id
            info.task_id = task_id
            info.process = process
            info.job_handle = job_handle
            info.log_file = open(log_path, "a", encoding="utf-8")
            info.log_path = log_path
            info.output_dir = str(output_dir)
            info.progress_token = progress_token
            info.log_size = 0
            info.log_truncated = False

            with self._runs_lock:
                self.active_runs[run_id] = info

            # ---- 写入数据库 ----
            conn.execute(
                "INSERT INTO runs "
                "(run_id, task_id, status, trigger_type, started_at, pid, final_command, "
                "param_snapshot, output_dir, log_path, intended_stop) "
                "VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    run_id, task_id, trigger_type, now, process.pid, command,
                    json.dumps(values, ensure_ascii=False),
                    str(output_dir), log_path,
                ),
            )
            conn.commit()

            # ---- 启动监控线程 ----
            t = threading.Thread(
                target=self._monitor_process,
                args=(run_id, stop_timeout, log_max_bytes),
                daemon=True,
            )
            info.monitor_thread = t
            t.start()

            return run_id

        finally:
            conn.close()

    # ========== 监控线程 ==========

    def _monitor_process(self, run_id: str, stop_timeout: int, log_max_bytes: int):
        """后台线程：读取日志 + 检测进程退出"""
        info = self.active_runs.get(run_id)
        if not info:
            return

        # ---- 日志读取循环 ----
        try:
            while True:
                line_bytes = info.process.stdout.readline()
                if not line_bytes:
                    if info.process.poll() is not None:
                        break
                    continue

                if info.log_truncated:
                    continue

                decoded = line_bytes.decode("utf-8", errors="replace")
                timestamp = datetime.now().strftime("[%H:%M:%S] ")
                entry = timestamp + decoded

                entry_bytes = entry.encode("utf-8")
                if info.log_size + len(entry_bytes) > log_max_bytes:
                    info.log_truncated = True
                    trunc_msg = f"{timestamp}[LOG TRUNCATED] 日志已达到大小上限，停止写入\n"
                    info.log_file.write(trunc_msg)
                    info.log_file.flush()
                    continue

                info.log_file.write(entry)
                info.log_file.flush()
                info.log_size += len(entry_bytes)

        except Exception:
            pass

        # ---- 进程已退出 ----
        exit_code = info.process.wait()

        if info.log_file:
            try:
                info.log_file.close()
            except Exception:
                pass

        # ---- 更新数据库 ----
        ended_at = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT started_at, intended_stop FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

            started_at = row["started_at"] if row else None
            intended_stop = row["intended_stop"] if row else 0

            duration_ms = 0
            if started_at:
                try:
                    start = datetime.fromisoformat(started_at)
                    end = datetime.fromisoformat(ended_at)
                    duration_ms = int((end - start).total_seconds() * 1000)
                except Exception:
                    pass

            log_size = 0
            try:
                log_size = os.path.getsize(info.log_path)
            except Exception:
                pass

            # 判定状态
            if intended_stop:
                status = "stopped"
            elif exit_code == 0:
                status = "success"
            else:
                status = "failed"

            # 失败快照
            if status == "failed":
                failure_lines = []
                try:
                    with open(info.log_path, "r", encoding="utf-8", errors="replace") as f:
                        all_lines = f.readlines()
                        failure_lines = [l.rstrip("\n\r") for l in all_lines[-50:]]
                except Exception:
                    pass
                conn.execute(
                    "UPDATE runs SET failure_summary = ? WHERE run_id = ?",
                    (
                        json.dumps(
                            {"exit_code": exit_code, "last_lines": failure_lines},
                            ensure_ascii=False,
                        ),
                        run_id,
                    ),
                )

            conn.execute(
                "UPDATE runs SET status = ?, ended_at = ?, duration_ms = ?, "
                "exit_code = ?, log_size_bytes = ?, log_truncated = ? WHERE run_id = ?",
                (
                    status, ended_at, duration_ms, exit_code,
                    log_size, 1 if info.log_truncated else 0, run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # ---- 清理内存 ----
        with self._runs_lock:
            self.active_runs.pop(run_id, None)

        if info.job_handle:
            try:
                close_job_object(info.job_handle)
            except Exception:
                pass

    # ========== 停止运行 ==========

    def stop_run(self, run_id: str, timeout: int | None = None) -> bool:
        """
        停止运行：关闭 Job Object 杀整个进程树 → 等待 → 关闭管道解除阻塞
        shell=True 时 terminate() 只杀 cmd.exe 不杀子进程，
        所以直接用 Job Object 确保整棵树都被清理。
        """
        info = self.active_runs.get(run_id)
        if not info or not info.process:
            return False

        # 标记主动停止
        self._mark_intended_stop(run_id)

        if timeout is None:
            timeout = self._get_stop_timeout(info.task_id)

        # Step 1: 关闭 Job Object，杀掉整个进程树（含所有子进程）
        if info.job_handle:
            try:
                close_job_object(info.job_handle)
            except Exception:
                pass
            info.job_handle = 0

        # Step 2: 等待主进程退出
        try:
            info.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # 兜底：强制 kill
            try:
                info.process.kill()
            except Exception:
                pass

        # Step 3: 关闭 stdout 管道，解除监控线程的 readline() 阻塞
        try:
            info.process.stdout.close()
        except Exception:
            pass

        # Step 4: 关闭日志文件句柄
        try:
            if info.log_file and not info.log_file.closed:
                info.log_file.close()
        except Exception:
            pass

        return True

    def force_kill_run(self, run_id: str) -> bool:
        """强制终止：直接关闭 Job Object + 关闭管道"""
        info = self.active_runs.get(run_id)
        if not info or not info.process:
            return False

        self._mark_intended_stop(run_id)

        # 关闭 Job Object 杀整棵树
        if info.job_handle:
            try:
                close_job_object(info.job_handle)
            except Exception:
                pass
            info.job_handle = 0

        # 关闭管道解除阻塞
        try:
            info.process.stdout.close()
        except Exception:
            pass

        # 关闭日志文件
        try:
            if info.log_file and not info.log_file.closed:
                info.log_file.close()
        except Exception:
            pass

        return True

    # ========== 进度回调 ==========

    def update_progress(self, run_id: str, token: str, data: dict) -> bool:
        """更新运行进度，校验 token"""
        info = self.active_runs.get(run_id)
        if not info:
            return False
        if info.progress_token != token:
            return False

        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO run_progress "
                "(run_id, percent, current, total, eta_sec, message, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    data.get("percent", 0),
                    data.get("current", 0),
                    data.get("total", 0),
                    data.get("eta_sec"),
                    data.get("message", ""),
                    now,
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ========== 查询 ==========

    def get_run_info(self, run_id: str) -> RunInfo | None:
        return self.active_runs.get(run_id)

    def is_running(self, run_id: str) -> bool:
        return run_id in self.active_runs

    # ========== 恢复 ==========

    def recover(self):
        """将数据库中仍为 running 但内存中不存在的 run 标记为 failed"""
        conn = self._get_conn()
        try:
            orphans = conn.execute(
                "SELECT run_id FROM runs WHERE status = 'running'"
            ).fetchall()

            now = datetime.now(timezone.utc).isoformat()
            count = 0
            for row in orphans:
                if row["run_id"] not in self.active_runs:
                    conn.execute(
                        "UPDATE runs SET status = 'failed', ended_at = ?, exit_code = -1 "
                        "WHERE run_id = ?",
                        (now, row["run_id"]),
                    )
                    count += 1

            conn.commit()
            if count:
                print(f"[RunManager] 恢复 {count} 个孤儿运行 → failed")
        finally:
            conn.close()

    # ========== 内部方法 ==========

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _mark_intended_stop(self, run_id: str):
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE runs SET intended_stop = 1 WHERE run_id = ?", (run_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def _get_stop_timeout(self, task_id: str) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT daemon_config FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row:
                cfg = json.loads(row["daemon_config"] or "{}")
                return cfg.get("stop_timeout", 5)
        finally:
            conn.close()
        return 5