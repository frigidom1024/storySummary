"""Reader 层：统一接口读取不同文件类型"""
from abc import ABC, abstractmethod
from pathlib import Path


class BookReader(ABC):
    """抽象基类，定义所有 Reader 的统一接口"""

    @abstractmethod
    def read(self) -> str:
        """读取完整文本内容（含元数据）"""

    @property
    @abstractmethod
    def title(self) -> str:
        """书名"""

    @property
    @abstractmethod
    def author(self) -> str:
        """作者"""

    @property
    def chapters(self) -> list[dict]:
        """章节列表，无章节结构时返回空列表"""
        return []

    @property
    def metadata(self) -> dict:
        """完整元数据"""
        return {}


def read_book(book_path: str) -> BookReader:
    """自动检测文件类型，返回对应 Reader"""
    path = Path(book_path)
    suffix = path.suffix.lower()

    if suffix == ".epub":
        from src.utils.reader.epub import EpubReader
        return EpubReader(book_path)
    elif suffix == ".pdf":
        from src.utils.reader.pdf import PdfReader
        return PdfReader(book_path)
    elif suffix == ".txt":
        from src.utils.reader.text import TxtReader
        return TxtReader(book_path)
    else:
        raise ValueError(
            f"Unsupported book format: {suffix}. Supported: .epub, .pdf, .txt"
        )
