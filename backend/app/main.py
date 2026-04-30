"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api import auth, audit, tasks, params, runs
from app.config import HOST, PORT
from app.core.run_manager import RunManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    init_db()
    # 恢复孤儿运行
    rm = RunManager.get_instance()
    rm.recover()
    print(f"[TaskMaster] 服务启动: http://{HOST}:{PORT}")
    yield
    # 关闭时：所有 Job Object 句柄关闭，进程树自动清理
    print("[TaskMaster] 服务关闭")


app = FastAPI(
    title="TaskMaster",
    version="1.0.0",
    description="本地脚本统一管理平台",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)