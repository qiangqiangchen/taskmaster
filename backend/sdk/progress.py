"""
TaskMaster 进度上报 SDK
脚本中直接使用：

    from progress import TaskProgress

    p = TaskProgress()
    p.report(percent=50, current=5, total=10, message="处理中...")
    p.save_output("result.json", json.dumps(data, ensure_ascii=False, indent=2))
"""
import os
import json
import urllib.request
import urllib.error


class TaskProgress:
    """任务进度上报工具"""

    def __init__(self):
        self.run_id = os.environ.get("TASK_RUN_ID", "")
        self.output_dir = os.environ.get("TASK_OUTPUT_DIR", "")
        self.progress_url = os.environ.get("TASK_PROGRESS_URL", "")
        self.token = os.environ.get("TASK_PROGRESS_TOKEN", "")
        self.workspace = os.environ.get("TASK_WORKSPACE", "")

    @property
    def available(self) -> bool:
        """是否在 TaskMaster 运行环境中"""
        return bool(self.run_id and self.progress_url and self.token)

    def report(
        self,
        percent: int | None = None,
        current: int | None = None,
        total: int | None = None,
        eta_sec: int | None = None,
        message: str = "",
    ) -> bool:
        """
        上报进度

        参数:
            percent: 完成百分比 0-100
            current: 当前处理数量
            total: 总数量
            eta_sec: 预计剩余秒数
            message: 进度消息
        """
        if not self.available:
            return False

        data = {
            "status": "running",
            "percent": percent if percent is not None else 0,
            "current": current if current is not None else 0,
            "total": total if total is not None else 0,
            "eta_sec": eta_sec,
            "message": message,
        }

        req = urllib.request.Request(
            self.progress_url,
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            return True
        except (urllib.error.URLError, OSError):
            return False

    def save_output(self, filename: str, content: str, encoding: str = "utf-8") -> str | None:
        """
        保存文本产物到输出目录

        参数:
            filename: 文件名（不含路径）
            content: 文本内容
            encoding: 编码

        返回: 保存路径，失败返回 None
        """
        if not self.output_dir:
            return None
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return path

    def save_output_bytes(self, filename: str, data: bytes) -> str | None:
        """
        保存二进制产物到输出目录

        参数:
            filename: 文件名（不含路径）
            data: 二进制数据

        返回: 保存路径，失败返回 None
        """
        if not self.output_dir:
            return None
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def output_path(self, filename: str) -> str:
        """获取产物文件的完整路径"""
        return os.path.join(self.output_dir, filename)

    def log(self, message: str):
        """打印带前缀的日志（方便在 TaskMaster 日志中区分）"""
        print(f"[TaskMaster] {message}", flush=True)


# 便捷单例
_progress = None


def get_progress() -> TaskProgress:
    global _progress
    if _progress is None:
        _progress = TaskProgress()
    return _progress