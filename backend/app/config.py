"""
全局配置模块
- 管理路径、密钥、端口等配置
- 自动创建工作区目录结构
"""
import os
import secrets
from pathlib import Path

# ========== 路径 ==========
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WORKSPACE_DIR = BASE_DIR / "workspace"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
WORKSPACE_DIR.mkdir(exist_ok=True)
(WORKSPACE_DIR / "scripts").mkdir(exist_ok=True)
(WORKSPACE_DIR / "inputs").mkdir(exist_ok=True)
(WORKSPACE_DIR / "outputs").mkdir(exist_ok=True)
(WORKSPACE_DIR / "logs").mkdir(exist_ok=True)

# ========== 数据库 ==========
DB_PATH = DATA_DIR / "taskmaster.db"

# ========== 密钥 ==========
SECRET_KEY_FILE = DATA_DIR / ".secret_key"


def get_or_create_secret_key() -> str:
    """获取或生成 JWT 密钥，持久化到文件"""
    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_text().strip()
    key = secrets.token_urlsafe(32)
    SECRET_KEY_FILE.write_text(key)
    return key


SECRET_KEY = get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# ========== 网络 ==========
HOST = os.getenv("TASKMASTER_HOST", "127.0.0.1")
PORT = int(os.getenv("TASKMASTER_PORT", "8765"))

# ========== 默认值 ==========
DEFAULT_PYTHON = os.getenv("TASKMASTER_PYTHON", "python")