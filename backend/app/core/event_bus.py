"""
进程内事件总线
- RunManager 通过它推送运行状态变更
- WebSocket 端点通过它接收实时事件
"""
import asyncio
import threading
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=200)
        with self._lock:
            self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        with self._lock:
            if run_id in self._subscribers:
                try:
                    self._subscribers[run_id].remove(queue)
                except ValueError:
                    pass
                if not self._subscribers[run_id]:
                    del self._subscribers[run_id]

    def publish(self, run_id: str, data: dict):
        with self._lock:
            queues = list(self._subscribers.get(run_id, []))
        for q in queues:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass

    def publish_sync(self, run_id: str, data: dict):
        """从同步线程调用（RunManager 的监控线程）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(lambda: self.publish(run_id, data))
            else:
                self.publish(run_id, data)
        except RuntimeError:
            # 没有 event loop，直接尝试
            self.publish(run_id, data)


event_bus = EventBus()