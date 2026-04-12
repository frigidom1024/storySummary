# 分块工具重构设计

## 目标

重构 `src/core/chunker.py` 和相关模块，建立清晰的职责分离：
- **Reader 层**（`src/utils/reader/`）：负责读取不同文件类型，提供完整内容（含元数据）和章节结构
- **Chunker 层**（`src/core/chunker.py`）：应用层接口，根据 book_id 返回分章节结果

## 现状问题

1. `src/core/chunker.py` 混合了应用层接口（`chunk_epub_by_id`）和通用文本分块逻辑（`SmartChunker`、`AdaptiveChunker`）
2. `src/utils/epub_chunker.py` 与 `core/chunker.py` 中的 `EpubChunker` 功能重复
3. `src/utils/book_adapter.py`、`src/utils/epub_reader.py` 职责边界不清晰
4. `src/utils/reader/` 目录不存在
5. `analyzer.py` 中的 `_read_epub()`、`_read_txt()` 直接读取文件，绕过了 `BookReader` 抽象
6. `ChapterChunker` 是 `AdaptiveChunker` 的无意义包装，应删除

## 目标结构

```
src/
  core/
    chunker.py           # 应用层唯一接口: chunk_by_book_id(book_id)
  utils/
    reader/
      __init__.py        # BookReader 抽象类 + read_book() 工厂函数
      epub.py            # EpubReader（提供 chapters + full text）
      pdf.py             # PdfReader（提供 chapters + full text）
      text.py            # SmartChunker, AdaptiveChunker, TextChunker（通用文本分块）
    book_adapter.py      # 删除（功能已合并到 reader/）
    epub_reader.py       # 删除（合并到 reader/epub.py）
    epub_chunker.py      # 删除（合并到 reader/）
```

## 接口设计

### 1. Reader 层（`src/utils/reader/`）

#### `BookReader` 抽象类（`__init__.py`）
```python
class BookReader(ABC):
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
    """自动检测文件类型，返回对应 Reader（.epub → EpubReader，.pdf → PdfReader）"""
```

#### `EpubReader`（`epub.py`）
```python
class EpubReader(BookReader):
    def __init__(self, epub_path: str)
    def read(self) -> str                    # 完整文本（含元数据）
    @property def title(self) -> str
    @property def author(self) -> str
    @property def chapters(self) -> list[dict]  # [{"title": str, "content": str, "order": int}]
    @property def metadata(self) -> dict
```

#### `PdfReader`（`pdf.py`）
```python
class PdfReader(BookReader):
    def __init__(self, pdf_path: str)
    def read(self) -> str
    @property def title(self) -> str
    @property def author(self) -> str
    @property def chapters(self) -> list[dict]  # 页面/章节结构
    @property def metadata(self) -> dict
```

#### 文本分块器（`text.py`）
用于无原生章节结构的纯文本（TXT 等），对原始文本进行模式检测分块：
```python
class TextChunker:
    def chunk(self, text: str) -> list[Chunk]

class SmartChunker:
    def chunk(self, text: str) -> list[Chunk]

class AdaptiveChunker:
    def chunk(self, text: str) -> list[Chunk]
```

### 2. Chunker 层（`src/core/chunker.py`）

```python
def chunk_by_book_id(book_id: str, data_path: str = "data") -> list[Chunk]:
    """
    应用层唯一接口：根据 book_id 分章节返回 chunks。

    数据流：
    1. 根据 book_id 定位书籍文件
    2. 调用 read_book() 获取 Reader
    3a. 如果 reader.chapters 非空（EPUB）：直接从 chapters 构建 chunks
    3b. 如果 reader.chapters 为空（PDF/TXT）：对全文调用 AdaptiveChunker 分块
    """
```

## 数据流

### 路径 A：EPUB（原生章节结构）
```
chunk_by_book_id(book_id)
  │
  ├─ 定位 epub 文件
  │
  ├─ read_book(epub_path) → EpubReader
  │     ├─ .chapters = [{"title": "第一章", "content": "...", "order": 0}, ...]
  │
  └─ 直接从 reader.chapters 构建 list[Chunk]
```

### 路径 B：PDF / TXT（无原生章节）
```
chunk_by_book_id(book_id)
  │
  ├─ 定位文件
  │
  ├─ read_book(path) → PdfReader / 直接读TXT
  │     └─ .chapters = []（空）
  │
  └─ AdaptiveChunker().chunk(reader.read())
        └─ 对全文进行模式检测分块 → list[Chunk]
```

## 实现步骤

1. 创建 `src/utils/reader/` 目录
2. 创建 `src/utils/reader/__init__.py`：搬入 `BookReader` 抽象类 + `read_book()` 工厂函数
3. 创建 `src/utils/reader/epub.py`：搬入 `EpubReader`（合并 `epub_reader.py`）
4. 创建 `src/utils/reader/pdf.py`：搬入 `PdfReader`（合并 `book_adapter.py` 中的实现）
5. 创建 `src/utils/reader/text.py`：搬入 `SmartChunker`、`AdaptiveChunker`、`TextChunker`（从 `core/chunker.py` 移出）
6. 重写 `src/core/chunker.py`：
   - 删除所有具体分块器实现（只剩 `chunk_by_book_id`）
   - 删除 `chunk_epub_by_id`、`chunk_epub` 旧接口
   - 删除 `ChapterChunker`（删除）
7. 删除 `src/utils/book_adapter.py`
8. 删除 `src/utils/epub_reader.py`
9. 删除 `src/utils/epub_chunker.py`

## 需要更新的调用方

| 文件 | 当前调用 | 改动 |
|------|----------|------|
| `src/pipeline.py` | `ChapterChunker().chunk(text)` | 改用 `chunk_by_book_id(book_id)` |
| `src/services/analyzer.py` | `ChapterChunker().chunk(text)`，`_read_epub()`、`_read_txt()` 直接读取 | 统一通过 `chunk_by_book_id()` |
| `tests/core/test_chunker.py` | `SmartChunker`、`AdaptiveChunker` | 改为从 `src.utils.reader.text` 导入 |
| `tests/core/test_node_generator.py` | `ChapterChunker()` | 改为 `AdaptiveChunker` |
| `src/generation/pipeline.py` | `ChapterChunker()` | 同上 |

## 待删减代码

- `src/core/chunker.py`：`EpubChunker`、`chunk_epub_by_id`、`chunk_epub`、`ChapterChunker`、所有文本分块器实现
- `src/utils/epub_chunker.py`：整个文件
- `src/utils/book_adapter.py`：整个文件
- `src/utils/epub_reader.py`：整个文件
