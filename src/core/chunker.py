"""应用层分块接口 - 根据 book_id 返回分章节结果"""
from pathlib import Path

from src.models.chunk import Chunk
from src.utils.reader import read_book


def chunk_by_book_id(book_id: str, data_path: str = "data") -> list[Chunk]:
    """
    应用层唯一接口：根据 book_id 分章节返回 chunks。

    数据流：
    1. 根据 book_id 定位书籍文件
    2. 调用 read_book() 获取 Reader
    3a. 有 .chapters（EPUB/PDF检测到章节）→ 直接从 chapters 构建 chunks
    3b. 无 .chapters（TXT/PDF无章节）→ AdaptiveChunker 对全文分块
    """
    from src.utils.reader.text import AdaptiveChunker

    book_dir = Path(data_path) / "books" / book_id
    if not book_dir.exists():
        raise FileNotFoundError(f"Book directory not found: {book_dir}")

    # 查找支持的文件
    epub_file = list(book_dir.glob("*.epub"))
    pdf_file = list(book_dir.glob("*.pdf"))
    txt_file = list(book_dir.glob("*.txt"))

    if epub_file:
        book_path = str(epub_file[0])
    elif pdf_file:
        book_path = str(pdf_file[0])
    elif txt_file:
        book_path = str(txt_file[0])
    else:
        raise FileNotFoundError(f"No supported book file found in {book_dir}")

    reader = read_book(book_path)

    # 策略选择
    if reader.chapters:
        # 路径 A：Reader 提供章节结构（EPUB 或 PDF 检测到章节）
        return _build_chunks_from_chapters(reader.chapters)
    else:
        # 路径 B：无章节结构，使用 AdaptiveChunker 对全文分块
        text = reader.read()
        return AdaptiveChunker().chunk(text)


def _build_chunks_from_chapters(chapters: list[dict]) -> list[Chunk]:
    """从 Reader 的 chapters 构建 list[Chunk]"""
    chunks = []
    for i, chapter in enumerate(chapters):
        content = chapter.get("content", "").strip()
        title = chapter.get("title", "")

        # 跳过空章节和无效标题
        if len(content) < 100:
            continue
        if title in ("未知", "Unknown", ""):
            continue

        chunks.append(Chunk(
            id=f"chunk-{i:04d}",
            text=content,
            chapter=title,
            order=i,
            content_type=chapter.get("content_type", "other"),
        ))
    return chunks
