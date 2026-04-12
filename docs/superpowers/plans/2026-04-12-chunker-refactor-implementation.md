# 分块工具重构实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构分块工具，建立 Reader/Chunker 清晰职责分离，`src/core/chunker.py` 只保留应用层接口 `chunk_by_book_id(book_id)`

**Architecture:**
- Reader 层（`src/utils/reader/`）：EpubReader、PdfReader、TxtReader，提供 chapters 和完整文本
- Chunker 层（`src/core/chunker.py`）：单一入口 `chunk_by_book_id(book_id)`，内部根据文件类型选择分块策略
- 删除重复代码：`book_adapter.py`、`epub_reader.py`、`epub_chunker.py`

**Tech Stack:** Python, epub/PDF parsing, re-based text chunking

---

## 文件结构

```
src/
  core/
    chunker.py           # 重写：只保留 chunk_by_book_id()
  utils/
    reader/
      __init__.py       # 新建：BookReader + read_book() 工厂
      epub.py           # 新建：EpubReader
      pdf.py            # 新建：PdfReader
      text.py           # 新建：TxtReader + TextChunker/SmartChunker/AdaptiveChunker
    __init__.py         # 修改：re-export from reader
    book_adapter.py     # 删除
    epub_reader.py      # 删除
    epub_chunker.py     # 删除
```

---

## Chunk 1: 创建 Reader 层

**Files:**
- Create: `src/utils/reader/__init__.py`
- Create: `src/utils/reader/epub.py`
- Create: `src/utils/reader/pdf.py`
- Create: `src/utils/reader/text.py`

### Task 1: 创建 reader 目录结构和 __init__.py

**Files:**
- Create: `src/utils/reader/__init__.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p src/utils/reader
touch src/utils/reader/__init__.py
```

- [ ] **Step 2: 编写 BookReader 抽象类和 read_book() 工厂函数**

```python
"""Reader 层：统一接口读取不同文件类型"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


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
```

- [ ] **Step 3: 提交**

```bash
git add src/utils/reader/__init__.py
git commit -m "feat(reader): 创建 reader 模块，定义 BookReader 抽象类和 read_book() 工厂"
```

### Task 2: 创建 EpubReader

**Files:**
- Create: `src/utils/reader/epub.py`

- [ ] **Step 1: 从现有 epub_reader.py 复制并适配**

将 `src/utils/epub_reader.py` 的 `EpubReader` 复制到 `src/utils/reader/epub.py`，不做修改（保持原有功能）。

- [ ] **Step 2: 更新 import 路径**

确保文件内部没有从 `src.utils.book_adapter` 的导入。

- [ ] **Step 3: 提交**

```bash
git add src/utils/reader/epub.py
git commit -m "feat(reader): 添加 EpubReader"
```

### Task 3: 创建 PdfReader

**Files:**
- Create: `src/utils/reader/pdf.py`

- [ ] **Step 1: 从 book_adapter.py 提取 PdfBookReader**

将 `src/utils/book_adapter.py` 中的 `PdfBookReader` 复制到 `src/utils/reader/pdf.py`，类名改为 `PdfReader`，继承 `BookReader`。

```python
"""PDF 文件读取器"""
from pathlib import Path
from src.utils.reader import BookReader


class PdfReader(BookReader):
    """读取 PDF 文件，提取文本和元数据"""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self._text: str = ""
        self._title: str = ""
        self._author: str = ""
        self._chapters: list[dict] = []
        self._metadata: dict = {}
        self._load_pdf()

    def _load_pdf(self):
        # ... 从 book_adapter.py 提取的现有逻辑 ...
        pass  # 完整实现在 book_adapter.py 的 PdfBookReader

    def read(self) -> str:
        return self._text

    @property
    def title(self) -> str:
        return self._title

    @property
    def author(self) -> str:
        return self._author

    @property
    def chapters(self) -> list[dict]:
        return self._chapters

    @property
    def metadata(self) -> dict:
        return self._metadata
```

- [ ] **Step 2: 提交**

```bash
git add src/utils/reader/pdf.py
git commit -m "feat(reader): 添加 PdfReader"
```

### Task 4: 创建 text.py（TxtReader + 文本分块器）

**Files:**
- Create: `src/utils/reader/text.py`

- [ ] **Step 1: 从 core/chunker.py 提取文本分块器**

将 `SmartChunker`、`AdaptiveChunker`、`TextChunker` 从 `src/core/chunker.py` 移出到 `src/utils/reader/text.py`。

- [ ] **Step 2: 添加 TxtReader**

```python
class TxtReader(BookReader):
    """读取 TXT 文件，无章节结构"""

    def __init__(self, txt_path: str):
        self.txt_path = Path(txt_path)
        self._title = self.txt_path.stem
        self._author = "Unknown"
        self._metadata = {}
        self._text = self._read_with_encoding_detection()

    def _read_with_encoding_detection(self) -> str:
        encodings = ['utf-8', 'gbk', 'gb2312']
        for encoding in encodings:
            try:
                return self.txt_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return self.txt_path.read_text(encoding='utf-8', errors='ignore')

    def read(self) -> str:
        return self._text

    @property
    def title(self) -> str:
        return self._title

    @property
    def author(self) -> str:
        return self._author

    @property
    def chapters(self) -> list[dict]:
        return []

    @property
    def metadata(self) -> dict:
        return self._metadata
```

- [ ] **Step 3: 提交**

```bash
git add src/utils/reader/text.py
git commit -m "feat(reader): 添加 TxtReader 和文本分块器"
```

---

## Chunk 2: 重写 core/chunker.py

**Files:**
- Modify: `src/core/chunker.py`

### Task 5: 重写 chunker.py

**Files:**
- Modify: `src/core/chunker.py:1-`

- [ ] **Step 1: 读取现有 core/chunker.py 确认需要保留的内容**

确认 `Chunk` 模型和 `chunk_epub_by_id` 的 book 定位逻辑。

- [ ] **Step 2: 重写文件内容（删除所有现有实现，包括 ChapterChunker、SmartChunker 等）**

整个文件被 `chunk_by_book_id()` 和 `_build_chunks_from_chapters()` 替换，原有的 `ChapterChunker`、`SmartChunker`、`AdaptiveChunker`、`TextChunker`、`EpubChunker` 等全部删除。

```python
"""应用层分块接口 - 根据 book_id 返回分章节结果"""
from pathlib import Path
from typing import Optional
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
            order=i
        ))
    return chunks
```

- [ ] **Step 3: 提交**

```bash
git add src/core/chunker.py
git commit -m "refactor(chunker): 重写为单一接口 chunk_by_book_id()"
```

---

## Chunk 3: 更新 src/utils/__init__.py（先于文件删除）

**Files:**
- Modify: `src/utils/__init__.py`

### Task 6: 更新 src/utils/__init__.py（必须在删除旧文件之前）

- [ ] **Step 1: 更新 __init__.py**

`src/utils/__init__.py` 当前从旧模块导入，删除前必须先更新：

```python
# 旧：
from src.utils.epub_reader import EpubReader, read_epub
from src.utils.book_adapter import BookReader, EpubBookReader, PdfBookReader, read_book

# 新：
from src.utils.reader import BookReader, read_book
from src.utils.reader.epub import EpubReader
from src.utils.reader.pdf import PdfReader
from src.utils.reader.text import TxtReader

__all__ = ["BookReader", "read_book", "EpubReader", "PdfReader", "TxtReader"]
```

注：`read_epub` 不在 `src/` 中任何地方被 import，仅本项目内部使用，安全删除。

- [ ] **Step 2: 提交**

```bash
git add src/utils/__init__.py
git commit -m "refactor(utils): 更新 __init__.py 指向新 reader 模块"
```

---

## Chunk 4: 删除废弃文件

**Files:**
- Delete: `src/utils/book_adapter.py`
- Delete: `src/utils/epub_reader.py`
- Delete: `src/utils/epub_chunker.py`

### Task 7: 删除废弃文件（必须在 Task 6 之后执行）

- [ ] **Step 1: 删除文件**

```bash
rm src/utils/book_adapter.py
rm src/utils/epub_reader.py
rm src/utils/epub_chunker.py
```

- [ ] **Step 2: 提交**

```bash
git add -A  # staging deletions
git commit -m "refactor: 删除废弃的 book_adapter, epub_reader, epub_chunker"
```

---

## Chunk 5: 更新调用方

**Files:**
- Modify: `src/pipeline.py`
- Modify: `src/services/analyzer.py`
- Modify: `tests/core/test_chunker.py`
- Modify: `tests/core/test_node_generator.py`

### Task 8: 更新 src/pipeline.py

**Files:**
- Modify: `src/pipeline.py:4`（imports）
- Modify: `src/pipeline.py:27`（self.chunker 初始化）
- Modify: `src/pipeline.py:52,134`（read_book import）
- Modify: `src/pipeline.py:63`（chunk 调用处）
- Modify: `src/pipeline.py:146`（chunk 调用处）

- [ ] **Step 1: 更新 src/core/chunker import**

```python
# 旧：
from src.core.chunker import ChapterChunker

# 新：
from src.core.chunker import chunk_by_book_id
```

- [ ] **Step 2: 删除 self.chunker 初始化**

删除 `self.chunker = ChapterChunker()`

- [ ] **Step 3: 更新 read_book import**

`pipeline.py` 第 52 行和 134 行从 `src.utils.book_adapter` import `read_book`，改为从 `src.utils.reader` import。

```python
# 旧：
from src.utils.book_adapter import read_book

# 新：
from src.utils.reader import read_book
```

- [ ] **Step 4: 更新 chunk 调用**

```python
# 旧：
chunks = self.chunker.chunk(novel_text)

# 新：
chunks = chunk_by_book_id(book_id)
```

- [ ] **Step 5: 提交**

```bash
git add src/pipeline.py
git commit -m "refactor(pipeline): 迁移到 chunk_by_book_id() 和 reader 模块"
```

### Task 9: 更新 src/services/analyzer.py

**Files:**
- Modify: `src/services/analyzer.py:6,23`（imports 和 __init__）
- Modify: `src/services/analyzer.py:51-62`（analyze 方法中的读取+分块逻辑）

- [ ] **Step 1: 更新 imports**

```python
# 删除
from src.core.chunker import ChapterChunker

# 添加
from src.core.chunker import chunk_by_book_id
```

- [ ] **Step 2: 删除 self.chunker = ChapterChunker()**

在 `__init__` 中删除 `self.chunker = ChapterChunker()`

- [ ] **Step 3: 重写 analyze() 方法中的读取和分块逻辑**

`analyzer.py` 的 `analyze()` 方法需要先保存文件到 `data/books/{book_id}/`，然后调用 `chunk_by_book_id(book_id)`。

关键变更：
1. 删除 `self._read_epub()` 和 `self._read_txt()` 的直接调用
2. `analyze()` 接收的 `file_path` 是上传的临时文件，需要先复制到 `data/books/{book_id}/` 目录
3. 调用 `chunk_by_book_id(book_id)` 获取 chunks

```python
# 在 analyze() 方法中，删除读取文件的逻辑：
# 旧：
if file_type == 'epub':
    text = await self._read_epub(file_path)
else:
    text = await self._read_txt(file_path)
chunks = self.chunker.chunk(text)

# 新：
# file_path 已保存到 data/books/{book_id}/，直接用 book_id 分块
chunks = chunk_by_book_id(book_id)
```

- [ ] **Step 4: 提交**

```bash
git add src/services/analyzer.py
git commit -m "refactor(analyzer): 迁移到 chunk_by_book_id()"
```

### Task 10: 更新测试文件

**Files:**
- Modify: `tests/core/test_chunker.py`
- Modify: `tests/core/test_node_generator.py`

- [ ] **Step 1: 更新 test_chunker.py imports**

```python
# 旧：
from src.core.chunker import TextChunker, ChapterChunker

# 新：
from src.utils.reader.text import TextChunker, AdaptiveChunker
```

- [ ] **Step 2: 更新测试中的 ChapterChunker 引用**

`TestChapterChunker` 类改为使用 `AdaptiveChunker`：
```python
class TestAdaptiveChunker:
    def test_extracts_chapters(self):
        text = "Chapter 1\n\nContent one.\n\nChapter 2\n\nContent two."
        chunker = AdaptiveChunker()
        chunks = chunker.chunk(text)
        # ... assertions
```

- [ ] **Step 3: 更新 test_node_generator.py imports**

```python
# 旧：
from src.core.chunker import ChapterChunker

# 新：
from src.utils.reader.text import AdaptiveChunker
```

- [ ] **Step 4: 提交**

```bash
git add tests/core/test_chunker.py tests/core/test_node_generator.py
git commit -m "refactor(tests): 迁移到 reader.text 模块"
```

---

## Chunk 6: 验证

- [ ] **Step 1: 运行测试确认重构正确**

```bash
pytest tests/core/test_chunker.py -v
```

- [ ] **Step 2: 运行测试确认 test_node_generator 正常**

```bash
pytest tests/core/test_node_generator.py -v
```

- [ ] **Step 3: 验证 import 无错误**

```bash
python -c "from src.core.chunker import chunk_by_book_id; print('OK')"
python -c "from src.utils.reader import read_book, BookReader; print('OK')"
python -c "from src.utils.reader.text import AdaptiveChunker; print('OK')"
```

- [ ] **Step 4: 提交验证**

```bash
git add -A
git commit -m "test: 验证分块工具重构 - 所有测试通过"
```
