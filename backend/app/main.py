"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.api import auth, audit, tasks, params, runs, logs, artifacts, ws, scheduler, settings, dashboard, maintenance, progress
from app.config import HOST, PORT
from app.core.run_manager import RunManager
from app.core.scheduler import Scheduler
from app.core.daemon import DaemonManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    rm = RunManager.get_instance()
    rm.recover()
    sch = Scheduler.get_instance()
    sch.start()
    dm = DaemonManager.get_instance()
    dm.start()
    print(f"[TaskMaster] 服务启动: http://{HOST}:{PORT}")
    yield
    dm.stop()
    sch.stop()
    print("[TaskMaster] 服务关闭")


app = FastAPI(
    title="TaskMaster",
    version="1.0.0",
    description="本地脚本统一管理平台",
    lifespan=lifespan,
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请查看后端日志"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(tasks.router)
app.include_router(params.router)
app.include_router(runs.router)
app.include_router(logs.router)
app.include_router(artifacts.router)
app.include_router(ws.router)
app.include_router(scheduler.router)
app.include_router(settings.router)
app.include_router(dashboard.router)
app.include_router(maintenance.router)
app.include_router(progress.router)



@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)