# Epub/Txt Upload Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 添加 epub 和 txt 文件上传功能，epub 自动提取元数据和封面填充书籍卡片。

**Architecture:**
- 前端 UploadArea.vue 改为文件上传组件，支持 drag & drop
- 后端新增 `POST /api/books/upload` 接口，使用 `ebooklib` 解析 epub
- 封面存储到 `data/covers/`，通过 `/api/covers/` 静态路由访问
- Book 模型和数据库新增 author/publisher/cover_url 字段

**Tech Stack:** Python (FastAPI, ebooklib), Vue 3 (TypeScript, Pinia), SQLite

---

## Chunk 1: Database & Book Model

**Files:**
- Modify: `src/storage/database.py` (lines 29-47)
- Modify: `src/models/book.py`
- Modify: `src/storage/database.py` (lines 96-137)

### Task 1: Update Python Book Model

**Files:**
- Modify: `src/models/book.py`

- [ ] **Step 1: Read current Book model**

```python
# src/models/book.py
```

- [ ] **Step 2: Add new fields to Book model**

```python
from pydantic import BaseModel
from datetime import datetime


class Book(BaseModel):
    id: str
    user_id: str
    title: str
    author: str | None = None
    publisher: str | None = None
    cover_url: str | None = None
    nodes_file_path: str
    status: str = "pending"
    is_deleted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Commit**

```bash
git add src/models/book.py
git commit -m "feat: add author, publisher, cover_url to Book model"
```

### Task 2: Database Migration

**Files:**
- Modify: `src/storage/database.py` (_init_db method)
- Modify: `src/storage/database.py` (create_book method)
- Modify: `src/storage/database.py` (get_book method)
- Modify: `src/storage/database.py` (get_books_for_user method)

- [ ] **Step 1: Read current database.py**

```bash
head -160 src/storage/database.py
```

- [ ] **Step 2: Add idempotent ALTER TABLE in _init_db**

In `_init_db`, after `CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id)`, add:

```python
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id)")

            # 迁移：添加新列（幂等）
            for col, dtype in [("author", "TEXT"), ("publisher", "TEXT"), ("cover_url", "TEXT")]:
                try:
                    conn.execute(f"ALTER TABLE books ADD COLUMN {col} {dtype}")
                except sqlite3.OperationalError:
                    pass
```

- [ ] **Step 3: Update create_book INSERT statement**

Change INSERT from:
```python
            conn.execute(
                """INSERT INTO books (id, user_id, title, nodes_file_path, status, is_deleted, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (book.id, book.user_id, book.title, book.nodes_file_path,
                 book.status, int(book.is_deleted), book.created_at)
            )
```
To:
```python
            conn.execute(
                """INSERT INTO books (id, user_id, title, author, publisher, cover_url, nodes_file_path, status, is_deleted, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (book.id, book.user_id, book.title, book.author, book.publisher,
                 book.cover_url, book.nodes_file_path, book.status, int(book.is_deleted), book.created_at)
            )
```

- [ ] **Step 4: Update get_book SELECT and return**

Change SELECT from:
```python
            row = conn.execute(
                """SELECT id, user_id, title, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE id = ? AND is_deleted = 0""",
                (book_id,)
            ).fetchone()
```
To:
```python
            row = conn.execute(
                """SELECT id, user_id, title, author, publisher, cover_url, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE id = ? AND is_deleted = 0""",
                (book_id,)
            ).fetchone()
```
And return mapping from:
```python
                return Book(
                    id=row[0], user_id=row[1], title=row[2],
                    nodes_file_path=row[3], status=row[4],
                    is_deleted=bool(row[5]), created_at=row[6]
                )
```
To:
```python
                return Book(
                    id=row[0], user_id=row[1], title=row[2],
                    author=row[3], publisher=row[4], cover_url=row[5],
                    nodes_file_path=row[6], status=row[7],
                    is_deleted=bool(row[8]), created_at=row[9]
                )
```

- [ ] **Step 5: Update get_books_for_user SELECT and return**

Change SELECT from:
```python
            rows = conn.execute(
                """SELECT id, user_id, title, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE user_id = ? AND is_deleted = 0 ORDER BY created_at DESC""",
                (user_id,)
            ).fetchall()
```
To:
```python
            rows = conn.execute(
                """SELECT id, user_id, title, author, publisher, cover_url, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE user_id = ? AND is_deleted = 0 ORDER BY created_at DESC""",
                (user_id,)
            ).fetchall()
```
And return mapping from:
```python
                return [
                    Book(
                        id=r[0], user_id=r[1], title=r[2],
                        nodes_file_path=r[3], status=r[4],
                        is_deleted=bool(r[5]), created_at=r[6]
                    )
                    for r in rows
                ]
```
To:
```python
                return [
                    Book(
                        id=r[0], user_id=r[1], title=r[2],
                        author=r[3], publisher=r[4], cover_url=r[5],
                        nodes_file_path=r[6], status=r[7],
                        is_deleted=bool(r[8]), created_at=r[9]
                    )
                    for r in rows
                ]
```

- [ ] **Step 6: Test database changes**

Run:
```bash
cd D:/project/storySummary && source .venv/Scripts/activate 2>/dev/null || true
python -c "
from src.storage.database import Database
db = Database('data/story_summary.db')
print('Database initialized successfully')
# Verify columns exist
import sqlite3
conn = sqlite3.connect('data/story_summary.db')
cursor = conn.execute('PRAGMA table_info(books)')
cols = [row[1] for row in cursor]
print('Columns:', cols)
assert 'author' in cols, 'author column missing'
assert 'publisher' in cols, 'publisher column missing'
assert 'cover_url' in cols, 'cover_url column missing'
print('All new columns present')
"
```

- [ ] **Step 7: Commit**

```bash
git add src/storage/database.py
git commit -m "feat: migrate books table with author, publisher, cover_url fields"
```

---

## Chunk 2: Backend Upload API

**Files:**
- Create: `src/services/epub_parser.py`
- Modify: `src/api/routers/books.py`
- Modify: `src/api/main.py`
- Modify: `src/api/schemas/book.py`

### Task 3: Install ebooklib

- [ ] **Step 1: Install dependency**

```bash
cd D:/project/storySummary && source .venv/Scripts/activate 2>/dev/null || true
pip install ebooklib
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore: add ebooklib for epub parsing"
```

### Task 4: Create epub Parser Service

**Files:**
- Create: `src/services/epub_parser.py`

- [ ] **Step 1: Write epub_parser.py**

```python
"""EPUB file parser service."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import io

try:
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False


@dataclass
class EpubMetadata:
    """Extracted metadata from an EPUB file."""
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    cover_image: Optional[bytes] = None
    cover_extension: Optional[str] = None  # jpg/png/gif


def parse_epub(file_bytes: bytes) -> EpubMetadata:
    """Parse an EPUB file and extract metadata.

    Args:
        file_bytes: Raw bytes of the EPUB file.

    Returns:
        EpubMetadata with extracted title, author, publisher, and cover.

    Raises:
        ValueError: If the file is not a valid EPUB.
    """
    if not HAS_EBOOKLIB:
        raise RuntimeError("ebooklib is not installed")

    try:
        book = epub.read_epub(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Invalid EPUB file: {e}")

    # Extract title
    title = None
    if book.get_metadata('DC', 'title'):
        title = book.get_metadata('DC', 'title')[0][0]
    elif book.get_metadata('OPF', 'title'):
        title = book.get_metadata('OPF', 'title')[0][0]

    # Extract author
    author = None
    if book.get_metadata('DC', 'creator'):
        author = book.get_metadata('DC', 'creator')[0][0]
    elif book.get_metadata('DC', 'author'):
        author = book.get_metadata('DC', 'author')[0][0]

    # Extract publisher
    publisher = None
    if book.get_metadata('DC', 'publisher'):
        publisher = book.get_metadata('DC', 'publisher')[0][0]

    # Extract cover image
    cover_image = None
    cover_extension = None

    for item in book.get_items():
        if item.get_type() == 9:  # MEDIA_TYPE.IMAGE
            item_href = item.get_name()
            if 'cover' in item_href.lower():
                cover_image = item.get_content()
                # Determine extension from MIME type or href
                if item.media_type:
                    ext = item.media_type.split('/')[-1]
                    if ext in ('jpeg', 'jpg', 'png', 'gif', 'webp'):
                        cover_extension = ext
                        if ext == 'jpeg':
                            cover_extension = 'jpg'
                if not cover_extension:
                    # Fallback: guess from href
                    if '.png' in item_href.lower():
                        cover_extension = 'png'
                    else:
                        cover_extension = 'jpg'
                break

    return EpubMetadata(
        title=title or '',
        author=author,
        publisher=publisher,
        cover_image=cover_image,
        cover_extension=cover_extension
    )
```

- [ ] **Step 2: Test epub parser (with a real epub file if available, or mock)**

```bash
cd D:/project/storySummary && source .venv/Scripts/activate 2>/dev/null || true
python -c "
from src.services.epub_parser import parse_epub
print('epub_parser module loads successfully')
"
```

- [ ] **Step 3: Commit**

```bash
git add src/services/epub_parser.py
git commit -m "feat: add epub parser service using ebooklib"
```

### Task 5: Add Static File Mount for Covers

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Read main.py**

```bash
cat src/api/main.py
```

- [ ] **Step 2: Add static files mount for covers**

Add after the CORS middleware setup, before registering routers:

```python
from fastapi.staticfiles import StaticFiles
import os

# 确保封面目录存在
os.makedirs("data/covers", exist_ok=True)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(books.router, prefix="/api")

# 封面静态文件路由（放在路由注册之后）
app.mount("/api/covers", StaticFiles(directory="data/covers"), name="covers")
```

- [ ] **Step 3: Commit**

```bash
git add src/api/main.py
git commit -m "feat: add static file mount for book covers at /api/covers"
```

### Task 6: Create Upload Endpoint

**Files:**
- Modify: `src/api/schemas/book.py`
- Modify: `src/api/routers/books.py`

- [ ] **Step 1: Read current book.py schemas**

```bash
cat src/api/schemas/book.py
```

- [ ] **Step 2: Add UploadResponse to schemas**

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BookResponse(BaseModel):
    id: str
    user_id: str
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    cover_url: Optional[str] = None
    nodes_file_path: str
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Read current books router**

```bash
cat src/api/routers/books.py
```

- [ ] **Step 4: Add upload endpoint to books router**

Add imports:
```python
from fastapi import UploadFile, File, Form
import os
import uuid
from src.services.epub_parser import parse_epub
```

Add upload endpoint before the list_books endpoint:

```python
@router.post("/upload", response_model=BookResponse, status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """上传 epub 或 txt 文件创建书籍。"""
    # 文件类型检查
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    ext = file.filename.lower().rsplit('.', 1)[-1] if '.' in file.filename else ''
    if ext not in ('epub', 'txt'):
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 epub 和 txt")

    # 读取文件内容
    file_bytes = await file.read()

    # 文件大小检查 (50MB)
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小超过 50MB")

    # 解析元数据
    book_title = title or ''
    book_author = author
    book_publisher = publisher
    cover_url = None
    cover_extension = None

    if ext == 'epub':
        try:
            metadata = parse_epub(file_bytes)
            book_title = title or metadata.title or '未知书名'
            book_author = author or metadata.author
            book_publisher = publisher or metadata.publisher
            if metadata.cover_image:
                cover_extension = metadata.cover_extension or 'jpg'
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # txt 文件编码检测
        try:
            file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                file_bytes.decode('gbk')
            except UnicodeDecodeError:
                try:
                    file_bytes.decode('gb2312')
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="无法解析文本编码，请使用 UTF-8、GBK 或 GB2312 编码")
        book_title = title or ''

    # 生成 book_id
    book_id = str(uuid.uuid4())

    # 保存封面文件
    if cover_extension and ext == 'epub':
        # 需要重新读取封面（因为上面已经 read 过一次）
        # 所以重构：先解析，再统一处理
        pass
    # 实际上面的逻辑有问题，重新读取封面图片
```

Wait, there's an issue - after `await file.read()`, the file pointer is at the end. Need to refactor. Let me rewrite:

```python
@router.post("/upload", response_model=BookResponse, status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """上传 epub 或 txt 文件创建书籍。"""
    import os
    import uuid

    # 文件类型检查
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    filename = file.filename
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    if ext not in ('epub', 'txt'):
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 epub 和 txt")

    # 读取文件内容
    file_bytes = await file.read()

    # 文件大小检查 (50MB)
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小超过 50MB")

    # 解析元数据
    book_title = title or ''
    book_author = author
    book_publisher = publisher
    cover_image = None
    cover_extension = None

    if ext == 'epub':
        try:
            # 保存文件到临时路径以便 ebooklib 读取
            import tempfile
            import shutil
            tmp_path = tempfile.NamedTemporaryFile(suffix='.epub', delete=False)
            tmp_path.write(file_bytes)
            tmp_path.close()

            from ebooklib import epub
            book = epub.read_epub(tmp_path.name)

            # 提取 title
            dc_titles = book.get_metadata('DC', 'title')
            if dc_titles:
                book_title = title or dc_titles[0][0] or '未知书名'
            else:
                book_title = title or '未知书名'

            # 提取 author
            dc_authors = book.get_metadata('DC', 'creator')
            if dc_authors:
                book_author = author or dc_authors[0][0]

            # 提取 publisher
            dc_publishers = book.get_metadata('DC', 'publisher')
            if dc_publishers:
                book_publisher = publisher or dc_publishers[0][0]

            # 提取封面
            for item in book.get_items():
                if item.get_type() == 9:  # IMAGE
                    item_href = item.get_name().lower()
                    if 'cover' in item_href:
                        cover_image = item.get_content()
                        if item.media_type:
                            ext_from_mime = item.media_type.split('/')[-1]
                            if ext_from_mime in ('jpeg', 'jpg', 'png', 'gif', 'webp'):
                                cover_extension = 'jpg' if ext_from_mime == 'jpeg' else ext_from_mime
                        if not cover_extension:
                            cover_extension = 'jpg' if '.png' not in item_href else 'png'
                        break

            # 清理临时文件
            os.unlink(tmp_path.name)
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"epub 文件格式错误: {e}")
    else:
        # txt 编码检测
        for encoding in ('utf-8', 'gbk', 'gb2312'):
            try:
                file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="无法解析文本编码")

    # 生成 book_id 和路径
    book_id = str(uuid.uuid4())
    nodes_file_path = f"data/books/{book_id}"

    # 保存封面
    if cover_image and cover_extension:
        covers_dir = "data/covers"
        os.makedirs(covers_dir, exist_ok=True)
        cover_path = os.path.join(covers_dir, f"{book_id}.{cover_extension}")
        with open(cover_path, 'wb') as f:
            f.write(cover_image)
        cover_url = f"/api/covers/{book_id}.{cover_extension}"

    # 创建书籍记录
    new_book = book_service.create_book_object(
        user_id=user_id,
        title=book_title,
        author=book_author,
        publisher=book_publisher,
        cover_url=cover_url,
        nodes_file_path=nodes_file_path
    )

    return BookResponse.model_validate(new_book)
```

- [ ] **Step 5: Add create_book_object to BookService (or create directly via DB)**

Check if BookService has a method to create book with all fields:

```bash
grep -n "create_book" src/services/book_service.py
```

Read book_service.py and add a method that accepts all fields, or modify the existing one.

```python
# src/services/book_service.py
def create_book_object(self, user_id: str, title: str, author: str | None, publisher: str | None, cover_url: str | None, nodes_file_path: str) -> Book:
    """Create a book with full fields."""
    book = Book(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        author=author,
        publisher=publisher,
        cover_url=cover_url,
        nodes_file_path=nodes_file_path,
        status="pending",
        is_deleted=False,
        created_at=datetime.now()
    )
    self.db.create_book(book)
    return book
```

- [ ] **Step 6: Test upload endpoint manually**

Start backend and test with curl:
```bash
# Test with a txt file
curl -X POST http://localhost:8000/api/books/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.txt" \
  -F "title=测试书籍"
```

- [ ] **Step 7: Commit**

```bash
git add src/api/routers/books.py src/api/schemas/book.py src/services/book_service.py
git commit -m "feat: add POST /api/books/upload endpoint for epub and txt files"
```

---

## Chunk 3: Frontend Changes

**Files:**
- Modify: `web/src/api/index.ts`
- Modify: `web/src/stores/books.ts`
- Modify: `web/src/components/UploadArea.vue`
- Modify: `web/src/components/BookCard.vue`

### Task 7: Update Frontend Book Type

**Files:**
- Modify: `web/src/api/index.ts`

- [ ] **Step 1: Update Book interface**

Change:
```typescript
export interface Book {
  id: string
  user_id: string
  title: string
  nodes_file_path: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
}
```
To:
```typescript
export interface Book {
  id: string
  user_id: string
  title: string
  author?: string
  publisher?: string
  cover_url?: string
  nodes_file_path: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
}
```

- [ ] **Step 2: Add upload method to api**

Add to `booksApi`:
```typescript
export const booksApi = {
  // ... existing methods

  uploadBook: (file: File, meta?: { title?: string; author?: string; publisher?: string }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (meta?.title) formData.append('title', meta.title)
    if (meta?.author) formData.append('author', meta.author)
    if (meta?.publisher) formData.append('publisher', meta.publisher)
    return api.post<Book>('/books/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
```

- [ ] **Step 3: Commit**

```bash
cd web && git add src/api/index.ts
git commit -m "feat: add uploadBook API method and update Book interface"
```

### Task 8: Update Books Store

**Files:**
- Modify: `web/src/stores/books.ts`

- [ ] **Step 1: Add uploadBook to store**

Add function:
```typescript
async function uploadBook(file: File, meta?: { title?: string; author?: string; publisher?: string }) {
  loading.value = true
  error.value = null
  try {
    const res = await booksApi.uploadBook(file, meta)
    books.value.unshift(res.data)
    return res.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '上传书籍失败'
    return null
  } finally {
    loading.value = false
  }
}
```

Add to return:
```typescript
return {
  // ... existing exports
  uploadBook,
}
```

- [ ] **Step 2: Commit**

```bash
cd web && git add src/stores/books.ts
git commit -m "feat: add uploadBook to books store"
```

### Task 9: Rewrite UploadArea Component

**Files:**
- Modify: `web/src/components/UploadArea.vue`

- [ ] **Step 1: Rewrite as file upload component**

Full replacement:

```vue
<template>
  <div class="upload-section">
    <!-- 初始状态：上传区域 -->
    <div
      v-if="!showForm && !uploading && !uploadResult"
      class="upload-area"
      :class="{ dragging: isDragging }"
      @click="triggerFileInput"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".epub,.txt"
        style="display: none"
        @change="handleFileSelect"
      />
      <div class="upload-content">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <span class="upload-text">拖拽 epub 或 txt 文件到此处，或点击选择</span>
        <span class="upload-hint">支持 .epub 和 .txt 格式</span>
      </div>
    </div>

    <!-- 上传中状态 -->
    <div v-else-if="uploading" class="upload-status">
      <div class="spinner"></div>
      <span>{{ statusMessage }}</span>
    </div>

    <!-- 上传结果状态 -->
    <div v-else-if="uploadResult" class="upload-result">
      <div v-if="uploadResult.success" class="result-success">
        <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 6L9 17l-5-5"/>
        </svg>
        <span>上传成功！</span>
        <button class="reset-btn" @click="reset">继续上传</button>
      </div>
      <div v-else class="result-error">
        <span>{{ uploadResult.error }}</span>
        <button class="reset-btn" @click="reset">重试</button>
      </div>
    </div>

    <!-- epub 预览表单 -->
    <div v-else-if="selectedFile?.type === 'epub'" class="preview-form">
      <div class="preview-header">
        <h3>确认上传信息</h3>
        <button class="close-btn" @click="reset">取消</button>
      </div>
      <div class="preview-body">
        <div v-if="epubMeta.cover_url" class="cover-preview">
          <img :src="epubMeta.cover_url" alt="封面" />
        </div>
        <div class="meta-form">
          <div class="form-group">
            <label>书名</label>
            <input v-model="formData.title" type="text" placeholder="书名" />
          </div>
          <div class="form-group">
            <label>作者</label>
            <input v-model="formData.author" type="text" placeholder="作者" />
          </div>
          <div class="form-group">
            <label>出版社</label>
            <input v-model="formData.publisher" type="text" placeholder="出版社" />
          </div>
        </div>
      </div>
      <button class="submit-btn" :disabled="!formData.title" @click="confirmUpload">确认上传</button>
    </div>

    <!-- txt 输入表单 -->
    <div v-else class="create-form">
      <div class="form-header">
        <h3>填写书籍信息</h3>
        <button class="close-btn" @click="reset">取消</button>
      </div>
      <form @submit.prevent="confirmUpload">
        <div class="form-group">
          <input
            v-model="formData.title"
            type="text"
            placeholder="输入书名（必填）"
            required
            autofocus
          />
        </div>
        <div class="form-group">
          <input
            v-model="formData.author"
            type="text"
            placeholder="作者（选填）"
          />
        </div>
        <div class="form-group">
          <input
            v-model="formData.publisher"
            type="text"
            placeholder="出版社（选填）"
          />
        </div>
        <button type="submit" class="submit-btn" :disabled="!formData.title.trim()">
          上传
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useBooksStore } from '../stores/books'

const store = useBooksStore()

const fileInput = ref<HTMLInputElement | null>(null)
const showForm = ref(false)
const isDragging = ref(false)
const uploading = ref(false)
const statusMessage = ref('')
const selectedFile = ref<{ file: File; type: 'epub' | 'txt' } | null>(null)
const uploadResult = ref<{ success: boolean; error?: string } | null>(null)

const formData = reactive({
  title: '',
  author: '',
  publisher: '',
})

const epubMeta = reactive({
  cover_url: '',
})

function triggerFileInput() {
  fileInput.value?.click()
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) processFile(file)
}

function handleFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) processFile(file)
}

async function processFile(file: File) {
  const ext = file.name.toLowerCase().split('.').pop()
  if (ext === 'epub') {
    selectedFile.value = { file, type: 'epub' }
    formData.title = file.name.replace(/\.epub$/i, '')
    // epub 需要前端预览，后端会提供封面 URL
    showForm.value = true
  } else if (ext === 'txt') {
    selectedFile.value = { file, type: 'txt' }
    showForm.value = true
  } else {
    uploadResult.value = { success: false, error: '不支持的文件类型' }
  }
}

async function confirmUpload() {
  if (!selectedFile.value || !formData.title.trim()) return

  uploading.value = true
  statusMessage.value = selectedFile.value.type === 'epub' ? '正在解析 epub...' : '正在上传...'
  showForm.value = false

  const result = await store.uploadBook(selectedFile.value.file, {
    title: formData.title.trim(),
    author: formData.author.trim() || undefined,
    publisher: formData.publisher.trim() || undefined,
  })

  uploading.value = false

  if (result) {
    uploadResult.value = { success: true }
  } else {
    uploadResult.value = { success: false, error: store.error || '上传失败' }
  }
}

function reset() {
  showForm.value = false
  isDragging.value = false
  uploading.value = false
  uploadResult.value = null
  selectedFile.value = null
  formData.title = ''
  formData.author = ''
  formData.publisher = ''
  epubMeta.cover_url = ''
  if (fileInput.value) fileInput.value.value = ''
}
</script>

<style scoped>
.upload-section {
  margin-bottom: 24px;
}

.upload-area {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
}

.upload-area:hover,
.upload-area.dragging {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: var(--color-text-tertiary);
}

.upload-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.upload-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.upload-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-result {
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.result-success {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #15803d;
}

.check-icon {
  width: 20px;
  height: 20px;
}

.result-error {
  color: #b91c1c;
}

.reset-btn {
  margin-left: auto;
  padding: 4px 12px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.preview-form,
.create-form {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.preview-header,
.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.preview-header h3,
.form-header h3 {
  font-size: var(--font-size-base);
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.close-btn:hover {
  background: var(--color-surface-hover);
}

.preview-body {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.cover-preview img {
  width: 120px;
  height: 160px;
  object-fit: cover;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}

.meta-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.submit-btn {
  width: 100%;
  padding: 12px 24px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd web && git add src/components/UploadArea.vue
git commit -m "feat: rewrite UploadArea as file upload component with epub/txt support"
```

### Task 10: Update BookCard Component

**Files:**
- Modify: `web/src/components/BookCard.vue`

- [ ] **Step 1: Add cover, author, publisher display**

Replace template with:
```vue
<template>
  <div class="book-card" @click="onClick">
    <div class="card-content">
      <div v-if="book.cover_url" class="card-cover">
        <img :src="book.cover_url" :alt="book.title" />
      </div>
      <div v-else class="card-cover placeholder">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
      </div>
      <div class="card-info">
        <div class="card-header">
          <h3 class="book-title">{{ book.title }}</h3>
          <span class="status-badge" :class="statusClass">{{ statusText }}</span>
        </div>
        <div v-if="book.author || book.publisher" class="book-meta">
          <span v-if="book.author" class="author">{{ book.author }}</span>
          <span v-if="book.author && book.publisher" class="separator">·</span>
          <span v-if="book.publisher" class="publisher">{{ book.publisher }}</span>
        </div>
        <div class="book-date">
          <span>{{ formatDate(book.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
```

Replace style with:
```vue
<style scoped>
.book-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.book-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary);
}

.card-content {
  display: flex;
  gap: 16px;
}

.card-cover {
  flex-shrink: 0;
  width: 80px;
  height: 110px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-cover.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-border-light);
  color: var(--color-text-tertiary);
}

.card-cover.placeholder svg {
  width: 32px;
  height: 32px;
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.book-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.status-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.status-pending {
  background: var(--color-border-light);
  color: var(--color-text-secondary);
}

.status-processing {
  background: rgba(251, 188, 4, 0.15);
  color: #b45309;
}

.status-completed {
  background: rgba(52, 168, 83, 0.12);
  color: #15803d;
}

.status-failed {
  background: rgba(234, 67, 53, 0.12);
  color: #b91c1c;
}

.book-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  display: flex;
  gap: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.separator {
  color: var(--color-text-tertiary);
}

.book-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: auto;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd web && git add src/components/BookCard.vue
git commit -m "feat: enhance BookCard with cover, author, publisher display"
```
