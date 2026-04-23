"""启动前端服务"""
from dotenv import load_dotenv
import os
import subprocess

# 从项目根目录加载 .env
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

port = os.getenv("VITE_PORT", "5188")

if __name__ == '__main__':
    os.chdir(os.path.join(root_dir, "web"))
    import platform
    if platform.system() == 'Windows':
        subprocess.run(f"npm run dev -- --port {port}", shell=True)
    else:
        subprocess.run(["npm", "run", "dev", "--", "--port", port])
