from pathlib import Path


class PathBuilder:
    """安全构建存储路径"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir).resolve()

    def build_user_dir(self, user_id: str) -> Path:
        """构建用户目录"""
        self._validate_id(user_id)
        return self.base_dir / user_id

    def build_book_dir(self, user_id: str, book_id: str) -> Path:
        """构建书籍目录"""
        self._validate_id(user_id)
        self._validate_id(book_id)
        return self.build_user_dir(user_id) / book_id

    def build_nodes_file(self, user_id: str, book_id: str) -> str:
        """构建 nodes.json 文件路径"""
        return str(self.build_book_dir(user_id, book_id) / "nodes.json")

    def _validate_id(self, id_str: str) -> None:
        """验证 ID 格式，防止路径遍历"""
        clean = id_str.replace('-', '').replace('_', '')
        if not clean.isalnum():
            raise ValueError(f"Invalid ID format: {id_str}")