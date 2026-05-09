@echo off
chcp 65001 >nul
echo =====================================
echo   TaskMaster 启动中...
echo =====================================

if not exist "backend" (
    echo 错误: 请在项目根目录运行此脚本
    pause
    exit /b 1
)

:: 创建数据目录
if not exist "data" mkdir data

:: 安装后端依赖
if not exist "backend\venv" (
    echo [1/4] 创建 Python 虚拟环境...
    cd backend
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
    cd ..
) else (
    echo [1/4] Python 虚拟环境已存在，跳过
)

:: 安装前端依赖
if not exist "frontend\node_modules" (
    echo [2/4] 安装前端依赖...
    cd frontend
    call npm install
    cd ..
) else (
    echo [2/4] 前端依赖已存在，跳过
)

:: 启动后端
echo [3/4] 启动后端服务...
cd backend
call venv\Scripts\activate
start "TaskMaster Backend" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..

:: 等待后端启动
timeout /t 2 /nobreak >nul

:: 启动前端
echo [4/4] 启动前端服务...
cd frontend
start "TaskMaster Frontend" npm run dev
cd ..

echo.
echo =====================================
echo   TaskMaster 已启动!
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo.
echo   关闭两个命令行窗口即可停止服务
echo =====================================
echo.
pause