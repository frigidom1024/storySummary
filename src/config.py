"""后端配置文件"""
from dotenv import load_dotenv
import os
from pathlib import Path

# 从项目根目录加载 .env 文件
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")


class Config:
    """后端配置项"""

    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

    # 服务器配置
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8005"))
    HOST = "0.0.0.0"

    # 数据库
    DATABASE_PATH = "data/story_summary.db"

    VECTOR_DB_DIR = "data/vector_store"
    DATA_DIR = "data"


config = Config()