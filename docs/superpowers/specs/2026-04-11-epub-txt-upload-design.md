# 上传功能设计文档

## 概述

为故事摘要应用添加 epub 和 txt 文件上传支持。epub 文件自动提取元数据（封面、作者、出版社）填充书籍卡片，txt 文件需用户手动输入元数据。

## 现状

当前上传组件（UploadArea.vue）仅支持手动输入书名创建书籍记录，无实际文件上传能力。

## 设计

### 1. 前端 — 文件上传组件

**文件：** `web/src/components/UploadArea.vue`

**功能：**
- drag & drop + 点击选择文件
- 支持 `.epub` 和 `.txt` 文件
- epub 上传后自动解析，提取书名、作者、出版社、封面
- txt 上传后弹出表单，让用户输入书名、作者、出版社（无封面）
- 上传过程显示进度/状态

**交互流程：**
1. 用户拖拽或点击选择文件
2. 检测文件类型：
   - `.epub` → 显示"正在解析..." → 解析完成后显示 BookCard 预览（封面、作者、出版社自动填充）
   - `.txt` → 显示输入表单，让用户填写书名、作者、出版社
3. 点击确认后调用 `POST /api/books/upload`

### 2. 前端 — BookCard 展示

**文件：** `web/src/components/BookCard.vue`

**改动：**
- 新增展示字段：`author`、`publisher`、`cover_url`
- 封面图片显示在卡片左侧（如果有）
- 无封面时显示默认占位图

### 3. 前端 — API 类型

**文件：** `web/src/api/index.ts`

**Book 接口新增字段：**
```typescript
export interface Book {
  id: string
  user_id: string
  title: string
  author?: string        // 新增
  publisher?: string      // 新增
  cover_url?: string       // 新增
  nodes_file_path: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
}
```

**stores/books.ts 新增方法：**
```typescript
async function uploadBook(file: File, meta?: {
  title?: string
  author?: string
  publisher?: string
}): Promise<Book | null>
```

### 4. 后端 — Python Book 模型

**文件：** `src/models/book.py`

**改动：** 新增 3 个可选字段
```python
class Book(BaseModel):
    id: str
    user_id: str
    title: str
    author: str | None = None          # 新增
    publisher: str | None = None       # 新增
    cover_url: str | None = None       # 新增
    nodes_file_path: str
    status: str = "pending"
    is_deleted: bool = False
    created_at: datetime
```

### 5. 后端 — 数据库迁移

**文件：** `src/storage/database.py`

**改动：** books 表新增 3 列（幂等迁移，Python try-catch 包裹）
```python
# 幂等迁移
for col, dtype in [("author", "TEXT"), ("publisher", "TEXT"), ("cover_url", "TEXT")]:
    try:
        conn.execute(f"ALTER TABLE books ADD COLUMN {col} {dtype}")
    except sqlite3.OperationalError:
        pass  # 列已存在
```

相关 SQL 查询（`get_book`、`get_books_for_user`、`create_book`）的 SELECT/INSERT 列名列表需同步更新，加上 `author, publisher, cover_url`。

### 6. 后端 — 新增上传接口

**文件：** `src/api/routers/books.py`

**接口：**
```
POST /api/books/upload
Content-Type: multipart/form-data
Authorization: Bearer {token}

file: (binary, required)
title: (string, optional) — 用户填写的书名，epub 会覆盖解析值，txt 为必填
author: (string, optional)
publisher: (string, optional)

Response: BookResponse
  - 201 Created
  - 400 Bad Request (不支持的文件类型 / epub 格式错误 / txt 编码错误)
  - 401 Unauthorized
  - 413 Payload Too Large (文件超过 50MB)
```

**处理流程：**
1. 接收 multipart：文件 + `title`、`author`、`publisher`（均为可选）
2. 检测文件类型：
   - `.epub` → 调用 `parse_epub(file)` 提取元数据（title/author/publisher/cover），**前端传入的字段覆盖 epub 解析值**
   - `.txt` → 使用前端传入的 title/author/publisher
3. 生成 `book_id`
4. 如有封面：保存到 `data/covers/{book_id}.{ext}`
5. 创建 Book 记录（`cover_url = /api/covers/{book_id}.{ext}`，无封面则为 null，`status = "pending"`；**注意：cover_url 存的是 URL 路径而非文件系统路径**）
6. 返回 Book 响应

**文件上传限制：**
- 最大 50MB
- 仅允许 `.epub` 和 `.txt` 扩展名
- 413 Payload Too Large 响应

**错误处理：**
- epub 解析失败：返回 400，提示"epub 文件格式错误"
- txt 文件：始终成功（纯文本无需解析）
- 数据库插入成功但封面保存失败：删除数据库记录，返回 500
- 封面保存成功但数据库插入失败：删除封面文件，返回 500

**txt 文件编码：**
- 按顺序尝试 UTF-8 → GBK → GB2312 解码
- 均失败时返回 400，提示"无法解析文本编码"

### 7. 后端 — epub 解析服务

**文件：** `src/services/epub_parser.py`（新建）

**功能：**
- `parse_epub(file_bytes) -> EpubMetadata`
  - 提取书名（title）
  - 提取作者（creator/author）
  - 提取出版社（publisher）
  - 提取封面图片二进制

**依赖：** `ebooklib` 库（Python package，`pip install ebooklib`）

```python
@dataclass
class EpubMetadata:
    title: str
    author: str | None
    publisher: str | None
    cover_image: bytes | None      # 二进制图片数据
    cover_extension: str | None    # jpg/png
```

### 8. 后端 — 文件存储

**目录：** `data/covers/`

**规则：** `data/covers/{book_id}.{ext}`

封面 URL 路径：`/api/covers/{book_id}.{ext}`

需在 `main.py` 中添加静态文件路由：
```python
from fastapi.staticfiles import StaticFiles
app.mount("/api/covers", StaticFiles(directory="data/covers"), name="covers")
```

## 实现顺序

1. 数据库迁移 + Book 模型更新（幂等 ALTER TABLE + SQL 查询更新）
2. 后端 `epub_parser.py` 服务（epub 解析 + txt 编码检测）
3. 静态文件路由（封面访问）— 早于上传接口，因为上传依赖此路由生成 cover_url
4. 后端 `POST /api/books/upload` 接口
5. 前端 `Book` 接口类型更新
6. 前端 `books` store 新增 `uploadBook`
7. 前端 `UploadArea.vue` 重构为文件上传组件
8. 前端 `BookCard.vue` 展示新字段（封面/作者/出版社）

## 依赖

- Python: `ebooklib` 库（用于解析 epub 文件）
- 前端无需新增依赖（使用原生 fetch/axios）
