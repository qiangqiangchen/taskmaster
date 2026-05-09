# TaskMaster

本地脚本统一管理平台

## 功能特性

- 📋 **任务管理** — 创建、编辑、复制、启停脚本任务
- ▶️ **运行控制** — 手动触发、优雅停止、强制终止
- ⏰ **定时调度** — Cron 定时、固定间隔、开机启动
- 🔄 **守护进程** — 崩溃自动重启、重启次数限制、窗口重置
- 📊 **仪表盘** — 运行统计、成功率、最近运行
- 📜 **运行日志** — 实时 WebSocket 推送、日志搜索
- 📁 **产物管理** — 输出文件浏览与下载
- 🔐 **审计日志** — 全操作审计追踪
- ⚙️ **系统设置** — 全局参数配置
- 🔑 **用户认证** — 登录鉴权

## 快速开始

### 方式一：本地启动

```bash
# Linux / macOS
chmod +x start.sh
./start.sh

# Windows
start.bat
```

### 方式二：Docker 启动

```bash
docker-compose up -d
```

访问 http://localhost 即可使用。

### 方式三：手动启动

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 默认账号

首次启动自动创建：

- 用户名：`admin`
- 密码：`admin123`

> ⚠️ 请在首次登录后立即修改密码

## 项目结构

```
taskmaster/
├── backend/                 # Python 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心模块（调度、守护、运行管理）
│   │   ├── services/       # 服务层
│   │   ├── utils/          # 工具函数
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库
│   │   └── main.py         # 入口
│   └── requirements.txt
├── frontend/               # Vue 前端
│   ├── src/
│   │   ├── api/           # API 调用
│   │   ├── components/    # 组件
│   │   ├── views/         # 页面
│   │   ├── styles/        # 全局样式
│   │   └── router/        # 路由
│   └── package.json
├── data/                   # 运行数据（自动创建）
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── nginx.conf
├── start.sh
├── start.bat
└── README.md
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + FastAPI + SQLite |
| 前端 | Vue 3 + Element Plus + Vite |
| 部署 | Docker + Nginx |

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `TASKMASTER_HOST` | `0.0.0.0` | 后端监听地址 |
| `TASKMASTER_PORT` | `8000` | 后端监听端口 |
| `TASKMASTER_SECRET` | `taskmaster-secret-key-change-in-production` | JWT 密钥 |
| `TASKMASTER_DATA_DIR` | `./data` | 数据存储目录 |

## License

MIT