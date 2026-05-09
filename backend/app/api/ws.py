"""
WebSocket 路由
- 实时推送运行状态变更
"""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.event_bus import event_bus

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/ws/runs/{run_id}")
async def run_status_ws(websocket: WebSocket, run_id: str):
    """运行状态 WebSocket：连接后实时推送运行状态变更事件"""
    await websocket.accept()
    queue = event_bus.subscribe(run_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(data)
            except asyncio.TimeoutError:
                # 心跳保活
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        event_bus.unsubscribe(run_id, queue)