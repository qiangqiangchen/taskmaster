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
import queue as queue_module
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
from app.core.event_bus import event_bus

class RunInfo:
    """运行实例的内存状态"""
    __slots__ = [
        "run_id", "task_id", "process", "job_handle",
        "log_file", "log_path", "output_dir", "progress_token",
        "log_size", "log_truncated", "progress",
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
        self.log_size: int = 0
        self.log_truncated: bool = False
        self.progress: dict = {}


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
                    self.stop_run(running["run_id"])
                else:
                    strategy = daemon_cfg.get("auto_conflict", "skip")
                    if strategy == "skip":

                        run_id = str(uuid.uuid4())
                        task_name = task["name"]
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            "INSERT INTO runs (run_id, task_id, task_name, status, trigger_type, started_at, ended_at, final_command) "
                            "VALUES (?, ?, ?, 'skipped', ?, ?, ?, '')",
                            (run_id, task_id, task_name, trigger_type, now, now),
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
            # 命令为空时，根据任务类型自动生成

            if not command.strip():
                entry_cfg = json.loads(task["entry_config"] or "{}")

                if task["type"] == "python_script":
                    python_path = entry_cfg.get("python_path", "python")
                    script_path = entry_cfg.get("script_path", "")
                    if script_path and os.path.isfile(script_path):
                        command = f'"{python_path}" "{script_path}"'
                    else:
                        script_dir = WORKSPACE_DIR / "scripts" / task_id
                        if script_dir.exists():
                            py_files = list(script_dir.glob("*.py"))
                            if py_files:
                                command = f'"{python_path}" "{py_files[0]}"'

                elif task["type"] == "executable":
                    exe_path = entry_cfg.get("exe_path", "")
                    if exe_path and os.path.isfile(exe_path):
                        command = f'"{exe_path}"'
                    else:
                        script_dir = WORKSPACE_DIR / "scripts" / task_id
                        if script_dir.exists():
                            exe_files = list(script_dir.glob("*.exe"))
                            if exe_files:
                                command = f'"{exe_files[0]}"'

                elif task["type"] == "project":
                    raise ValueError("多文件项目必须指定命令模板")

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
            env["PYTHONUNBUFFERED"] = "1"
            # 注入 SDK 路径到 PYTHONPATH，让脚本可以直接 from progress import TaskProgress
            sdk_dir = str(Path(__file__).resolve().parent.parent.parent / "sdk")
            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                env["PYTHONPATH"] = sdk_dir + os.pathsep + existing_pythonpath
            else:
                env["PYTHONPATH"] = sdk_dir

            for k, v in json.loads(task["env_vars"] or "{}").items():
                if k not in env:
                    env[k] = str(v)
            for k, v in env_vars.items():
                if k not in env:
                    env[k] = str(v)

            # work_dir = task["work_dir"] or str(WORKSPACE_DIR)
            work_dir = task["work_dir"] or str(output_dir)

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

            daemon_cfg = json.loads(task["daemon_config"] or "{}")
            stop_timeout = daemon_cfg.get("stop_timeout", 5)

            job_handle = create_job_object()

            entry_cfg = json.loads(task["entry_config"] or "{}")
            creation_flags = 0
            if task["type"] == "executable" and entry_cfg.get("no_window"):
                creation_flags = 0x08000000

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=work_dir,
                creationflags=creation_flags,
                shell=True,
            )

            assign_process_to_job(job_handle, process.pid)

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

            task_name = task["name"]
            conn.execute(
                "INSERT INTO runs "
                "(run_id, task_id, task_name, status, trigger_type, started_at, pid, final_command, "
                "param_snapshot, output_dir, log_path, intended_stop) "
                "VALUES (?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    run_id, task_id, task_name, trigger_type, now, process.pid, command,
                    json.dumps(values, ensure_ascii=False),
                    str(output_dir), log_path,
                ),
            )
            conn.commit()

            t = threading.Thread(
                target=self._monitor_process,
                args=(run_id, stop_timeout, log_max_bytes),
                daemon=True,
            )
            t.start()

            return run_id

        finally:
            conn.close()

    # ========== 监控线程 ==========

    def _monitor_process(self, run_id: str, stop_timeout: int, log_max_bytes: int):
        """
        后台线程：读取日志 + 检测进程退出
        三个线程协作：
        - reader: 逐行读取 stdout 放入 Queue
        - waiter: 调用 process.wait()，进程退出后关闭 stdout 解除 reader 阻塞
        - 主监控: 从 Queue 取行写日志，检查退出事件
        """
        info = self.active_runs.get(run_id)
        if not info:
            return

        lines_queue = queue_module.Queue()
        process_done = threading.Event()

        def reader():
            """逐行读取 stdout"""
            while True:
                try:
                    line = info.process.stdout.readline()
                except (ValueError, OSError):
                    break
                if not line:
                    break
                lines_queue.put(line)
            lines_queue.put(None)

        def waiter():
            """等待进程退出，然后强制关闭 stdout"""
            info.process.wait()
            process_done.set()
            try:
                info.process.stdout.close()
            except Exception:
                pass

        threading.Thread(target=reader, daemon=True).start()
        threading.Thread(target=waiter, daemon=True).start()

        # 主循环：处理日志行 + 检测退出
        while True:
            try:
                line_bytes = lines_queue.get(timeout=0.5)
            except queue_module.Empty:
                if process_done.is_set():
                    self._drain_queue(info, lines_queue, log_max_bytes)
                    break
                continue

            if line_bytes is None:
                break

            self._write_log_line(info, line_bytes, log_max_bytes)

        # 确保进程被回收
        exit_code = info.process.returncode
        if exit_code is None:
            try:
                exit_code = info.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                exit_code = -1

        # 关闭日志文件
        try:
            if info.log_file and not info.log_file.closed:
                info.log_file.close()
        except Exception:
            pass

        # 更新数据库
        self._finalize_run(run_id, info, exit_code)

        # 清理内存
        with self._runs_lock:
            self.active_runs.pop(run_id, None)

        if info.job_handle:
            try:
                close_job_object(info.job_handle)
            except Exception:
                pass

    def _drain_queue(self, info, lines_queue, log_max_bytes):
        """排空队列中剩余的日志行"""
        try:
            line_bytes = lines_queue.get(timeout=2.0)
            if line_bytes is not None:
                self._write_log_line(info, line_bytes, log_max_bytes)
        except queue_module.Empty:
            pass

        while True:
            try:
                lb = lines_queue.get(timeout=0.1)
                if lb is None:
                    break
                self._write_log_line(info, lb, log_max_bytes)
            except queue_module.Empty:
                break

    def _write_log_line(self, info, line_bytes: bytes, log_max_bytes: int):
        """写入一行日志到文件"""
        if info.log_truncated:
            return

        # 解码：优先 UTF-8，回退 GBK（Windows cmd）
        try:
            decoded = line_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                decoded = line_bytes.decode("gbk", errors="replace")
            except Exception:
                decoded = line_bytes.decode("utf-8", errors="replace")

        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        entry = timestamp + decoded

        # 检测进度行
        stripped = decoded.strip()
        if stripped.startswith("[PROGRESS]"):
            try:
                prog = json.loads(stripped[10:])
                info.progress = prog
                self.update_progress(info.run_id, info.progress_token, prog)
            except Exception:
                pass
            return

        entry_bytes = entry.encode("utf-8")
        if info.log_size + len(entry_bytes) > log_max_bytes:
            info.log_truncated = True
            trunc_msg = f"{timestamp}[LOG TRUNCATED] 日志已达到大小上限，停止写入\n"
            try:
                info.log_file.write(trunc_msg)
                info.log_file.flush()
            except Exception:
                pass
            return

        try:
            info.log_file.write(entry)
            info.log_file.flush()
        except Exception:
            pass
        info.log_size += len(entry_bytes)

    def _finalize_run(self, run_id: str, info, exit_code: int):
        """更新运行状态到数据库"""
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

            if intended_stop:
                status = "stopped"
            elif exit_code == 0:
                status = "success"
            else:
                status = "failed"

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

            # 发布 WebSocket 事件
            event_bus.publish_sync(run_id, {
                "type": "run_status",
                "run_id": run_id,
                "status": status,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
            })
        finally:
            conn.close()
    # ========== 停止运行 ==========

    def stop_run(self, run_id: str, timeout: int | None = None) -> bool:
        """停止运行：关闭 Job Object 杀整个进程树 → 关闭管道解除阻塞"""
        info = self.active_runs.get(run_id)
        if not info or not info.process:
            return False

        self._mark_intended_stop(run_id)

        if timeout is None:
            timeout = self._get_stop_timeout(info.task_id)

        if info.job_handle:
            try:
                close_job_object(info.job_handle)
            except Exception:
                pass
            info.job_handle = 0

        try:
            info.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                info.process.kill()
            except Exception:
                pass

        try:
            info.process.stdout.close()
        except Exception:
            pass

        try:
            if info.log_file and not info.log_file.closed:
                info.log_file.close()
        except Exception:
            pass

        return True

    def force_kill_run(self, run_id: str) -> bool:
        """强制终止：关闭 Job Object + 关闭管道"""
        info = self.active_runs.get(run_id)
        if not info or not info.process:
            return False

        self._mark_intended_stop(run_id)

        if info.job_handle:
            try:
                close_job_object(info.job_handle)
            except Exception:
                pass
            info.job_handle = 0

        try:
            info.process.stdout.close()
        except Exception:
            pass

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