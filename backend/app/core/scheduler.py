"""
定时调度器
- 后台线程轮询 schedule 表
- 到期触发运行
- 自动计算下次执行时间
"""
import json
import threading
import time
import sqlite3
from datetime import datetime, timezone, timedelta

from app.database import DB_PATH
from app.core.cron import next_run, validate_cron
from app.core.run_manager import RunManager


class Scheduler:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._thread = None
        self._running = False
        self._reload_event = threading.Event()

    @classmethod
    def get_instance(cls) -> "Scheduler":
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
        print("[Scheduler] 调度器已启动")

    def stop(self):
        self._running = False
        self._reload_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[Scheduler] 调度器已停止")

    def reload(self):
        print("[Scheduler] 收到重载信号")
        self._reload_event.set()

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"[Scheduler] tick 异常: {e}")

            self._reload_event.clear()
            self._reload_event.wait(timeout=30)

    def _tick(self):
        now = datetime.now(timezone.utc)
        conn = self._get_conn()
        try:
            schedules = conn.execute(
                "SELECT s.*, t.enabled as task_enabled, t.name as task_name "
                "FROM schedules s JOIN tasks t ON s.task_id = t.task_id "
                "WHERE s.enabled = 1"
            ).fetchall()

            if schedules:
                print(f"[Scheduler] 检查 {len(schedules)} 个调度, 当前UTC: {now.strftime('%H:%M:%S')}")

            for sch in schedules:
                if not sch["task_enabled"]:
                    continue

                schedule_id = sch["schedule_id"]
                task_id = sch["task_id"]
                schedule_type = sch["schedule_type"]
                next_run_at = sch["next_run_at"]

                # 没有下次执行时间，先算一个
                if not next_run_at:
                    new_next = self._calc_next(schedule_type, sch)
                    conn.execute(
                        "UPDATE schedules SET next_run_at = ? WHERE schedule_id = ?",
                        (new_next, schedule_id),
                    )
                    if new_next:
                        print(f"[Scheduler] {sch['task_name']}: 设置下次执行 {new_next}")
                    continue

                # 解析 next_run_at
                try:
                    nr_time = datetime.fromisoformat(next_run_at)
                    if nr_time.tzinfo is None:
                        nr_time = nr_time.replace(tzinfo=timezone.utc)
                except Exception:
                    new_next = self._calc_next(schedule_type, sch)
                    conn.execute(
                        "UPDATE schedules SET next_run_at = ? WHERE schedule_id = ?",
                        (new_next, schedule_id),
                    )
                    continue

                # 判断是否到期
                if nr_time <= now:
                    print(f"[Scheduler] {sch['task_name']}: 到期触发 (next={nr_time.strftime('%H:%M:%S')}, now={now.strftime('%H:%M:%S')})")
                    try:
                        rm = RunManager.get_instance()
                        run_id = rm.start_run(task_id, trigger_type=schedule_type)
                        print(f"[Scheduler] {sch['task_name']}: 已触发 run_id={run_id[:8]}...")
                    except ValueError as e:
                        print(f"[Scheduler] {sch['task_name']}: 跳过 - {e}")
                    except Exception as e:
                        print(f"[Scheduler] {sch['task_name']}: 触发失败 - {e}")

                    # 更新 last_run_at 和 next_run_at
                    now_str = now.isoformat()
                    new_next = self._calc_next(schedule_type, sch)
                    conn.execute(
                        "UPDATE schedules SET last_run_at = ?, next_run_at = ? WHERE schedule_id = ?",
                        (now_str, new_next, schedule_id),
                    )
                    print(f"[Scheduler] {sch['task_name']}: 下次执行 {new_next}")

            conn.commit()
        finally:
            conn.close()

    def _calc_next(self, schedule_type: str, sch) -> str | None:
        if schedule_type == "cron":
            cron_expr = sch["cron_expression"]
            if not cron_expr:
                return None
            try:
                nr = next_run(cron_expr)
                if nr:
                    return nr.isoformat()
            except Exception as e:
                print(f"[Scheduler] cron 计算失败: {e}")
            return None
        elif schedule_type == "interval":
            interval = sch["interval_seconds"]
            if not interval or interval <= 0:
                return None
            nr = datetime.now(timezone.utc) + timedelta(seconds=interval)
            return nr.isoformat()
        return None

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn