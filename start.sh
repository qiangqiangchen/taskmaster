#!/bin/bash
# TaskMaster 本地启动脚本

set -e

echo "====================================="
echo "  TaskMaster 启动中..."
echo "====================================="

# 检查后端
if [ ! -d "backend" ]; then
    echo "错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "backend/venv" ]; then
    echo "[1/4] 创建 Python 虚拟环境..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo "[1/4] Python 虚拟环境已存在，跳过"
fi

# 安装前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "[2/4] 安装前端依赖..."
    cd frontend
    npm install
    cd ..
else
    echo "[2/4] 前端依赖已存在，跳过"
fi

# 创建数据目录
mkdir -p data

# 启动后端
echo "[3/4] 启动后端服务..."
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 启动前端
echo "[4/4] 启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "====================================="
echo "  TaskMaster 已启动!"
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  API 文档: http://localhost:8000/docs"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "====================================="
echo ""

# 捕获退出信号
trap "echo '正在停止...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait