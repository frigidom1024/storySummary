import json
import tempfile
import os
from pathlib import Path


class JsonStorage:
    """JSON 文件存储，支持原子写入"""

    def read(self, file_path: str) -> dict:
        """读取 JSON 文件"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def write(self, file_path: str, data: dict) -> None:
        """
        原子写入 JSON 文件：
        1. 先写入临时文件
        2. 再 rename 到目标文件（原子操作）
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=path.parent)
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def delete(self, file_path: str) -> None:
        """删除 JSON 文件"""
        path = Path(file_path)
        if path.exists():
            os.remove(path)