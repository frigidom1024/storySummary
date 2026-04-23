"""启动后端服务"""
from dotenv import load_dotenv
import os
import uvicorn

# 从项目根目录加载 .env
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

port = int(os.getenv("BACKEND_PORT", "8005"))

if __name__ == '__main__':
    os.chdir(root_dir)
    os.environ['PYTHONPATH'] = root_dir
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=port,
        reload=True,
    )
