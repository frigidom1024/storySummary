# 分块工具重构设计

## 目标

重构 `src/core/chunker.py` 和相关模块，建立清晰的职责分离：
- **Reader 层**（`src/utils/reader/`）：负责读取不同文件类型，提供完整内容（含元数据）
- **Chunker 层**（`src/core/chunker.py`）：应用层接口，根据 book_id 返回分章节结果

## 现状问题

1. `src/core/chunker.py` 混合了应用层接口（`chunk_epub_by_id`）和通用文本分块逻辑（`SmartChunker`、`AdaptiveChunker`）
2. `src/utils/epub_chunker.py` 与 `core/chunker.py` 中的 `EpubChunker` 功能重复
3. `src/utils/book_adapter.py`、`src/utils/epub_reader.py` 职责边界不清晰
4. `src/utils/reader/` 目录不存在

## 目标结构

```
src/
  core/
    chunker.py           # 应用层唯一接口: chunk_by_book_id(book_id)
  utils/
    reader/
      __init__.py        # read_book() 工厂函数
      epub.py            # EpubReader + EPUB分块
      pdf.py             # PdfReader + PDF分块
      text.py            # SmartChunker, AdaptiveChunker, TextChunker
    book_adapter.py      # 删除（合并到 reader/）
    epub_reader.py       # 删除（合并到 reader/epub.py）
    epub_chunker.py      # 删除（合并到 reader/）
```

## 接口设计

### 1. Reader 层（`src/utils/reader/`）

#### `EpubReader`（`epub.py`）
```python
class EpubReader:
    def read(self) -> str                    # 完整文本（含元数据、封面、目录）
    @property def title(self) -> str         # 书名
    @property def author(self) -> str         # 作者
    @property def chapters(self) -> list[dict]  # [{"title": str, "content": str, "order": int}]
    @property def metadata(self) -> dict      # 完整元数据
```

#### `PdfReader`（`pdf.py`）
```python
class PdfReader:
    def read(self) -> str                    # 完整文本
    @property def title(self) -> str
    @property def author(self) -> str
    @property def chapters(self) -> list[dict]  # 页面/章节结构
    @property def metadata(self) -> dict
```

#### `TextChunker`（`text.py`）
用于无结构化章节的纯文本（txt 等）：
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

    1. 根据 book_id 找到书籍文件（epub/pdf）
    2. 调用 read_book() 读取，获取 chapters
    3. 返回分章节后的 list[Chunk]
    """
```

### 3. 工厂函数（`src/utils/reader/__init__.py`）

```python
def read_book(book_path: str) -> BookReader:
    """自动检测文件类型，返回对应 Reader"""

class BookReader(ABC):
    @abstractmethod
    def read(self) -> str: ...
    @property @abstractmethod def title(self) -> str: ...
    @property @abstractmethod def author(self) -> str: ...
    @property def chapters(self) -> list[dict]: return []
```

## 数据流

```
chunk_by_book_id(book_id)
  │
  ├─ 根据 book_id 定位书籍文件
  │
  ├─ read_book(epub_path) → EpubReader
  │     ├─ .title, .author, .metadata
  │     └─ .chapters = [{"title": "第一章", "content": "...", "order": 0}, ...]
  │
  └─ AdaptiveChunker().chunk(reader.chapters)
        └─ 返回 list[Chunk]
```

## 实现步骤

1. 创建 `src/utils/reader/` 目录
2. 将 `src/utils/epub_reader.py` 内容合并到 `src/utils/reader/epub.py`
3. 将 `src/utils/book_adapter.py` 的 `PdfBookReader` 移到 `src/utils/reader/pdf.py`
4. 将 `src/utils/book_adapter.py` 的 `BookReader` 抽象类移到 `src/utils/reader/__init__.py`
5. 将 `src/core/chunker.py` 中的 `SmartChunker`、`AdaptiveChunker`、`TextChunker` 移到 `src/utils/reader/text.py`
6. 重写 `src/core/chunker.py`，只保留 `chunk_by_book_id()` 应用层接口
7. 删除 `src/utils/epub_chunker.py`
8. 更新所有调用方（`pipeline.py`、`analyzer.py` 等）

## 兼容性

- `pipeline.py` 中 `ChapterChunker` 替换为 `AdaptiveChunker`
- 删除 `chunk_epub_by_id` 和 `chunk_epub` 旧接口，统一使用 `chunk_by_book_id`
