# 数据库存储重构设计文档

## 1. 概述与目标

**项目名称：** Story Summary 后端存储重构
**项目类型：** 架构重构（保持技术栈不变）
**核心目标：** 面向接口设计，数据库存用户+索引，Nodes 存 JSON 文件

**技术栈（保持不变）：**
- FastAPI：REST API
- SQLite：关系数据存储
- ChromaDB：向量存储
- Pydantic：数据验证

---

## 2. 存储结构

### 2.1 文件系统

```
data/
└── {user_id}/
    └── {book_id}/
        └── nodes.json    # 该书的所有叙事节点
```

### 2.2 JSON 文件格式

`nodes.json` 结构：
```json
{
  "book_id": "uuid",
  "nodes": [
    {
      "id": "node-1",
      "scene": "...",
      "characters": [...],
      ...
    }
  ],
  "structure": {
    "opening": ["node-1", "node-2"],
    "rising": [...],
    "climax": [...],
    "ending": [...]
  }
}
```

---

## 3. 数据库表结构

### 3.1 users 表

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    profile TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID，主键 |
| username | TEXT | 用户名，唯一 |
| email | TEXT | 邮箱，唯一 |
| password_hash | TEXT | 密码哈希 |
| profile | TEXT | JSON，用户配置 |
| created_at | TIMESTAMP | 创建时间 |

### 3.2 books 表

```sql
CREATE TABLE books (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    nodes_file_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID，主键 |
| user_id | TEXT | 外键，关联用户 |
| title | TEXT | 书名 |
| nodes_file_path | TEXT | nodes.json 文件路径 |
| status | TEXT | pending/processing/completed/failed |
| created_at | TIMESTAMP | 创建时间 |

---

## 4. 服务接口设计

### 4.1 接口定义

```python
# src/services/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.user import User
from src.models.book import Book
from src.models.narrative_node import NarrativeNode, StoryStructure

class IUserService(ABC):
    @abstractmethod
    def create_user(self, username: str, email: str, password: str) -> User: ...

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Optional[User]: ...

    @abstractmethod
    def update_profile(self, user_id: str, profile: dict) -> User: ...


class IBookService(ABC):
    @abstractmethod
    def create_book(self, user_id: str, title: str) -> Book: ...

    @abstractmethod
    def get_book(self, book_id: str) -> Optional[Book]: ...

    @abstractmethod
    def get_books_for_user(self, user_id: str) -> List[Book]: ...

    @abstractmethod
    def update_book_status(self, book_id: str, status: str) -> Book: ...

    @abstractmethod
    def delete_book(self, book_id: str) -> None: ...


class INodeService(ABC):
    @abstractmethod
    def save_nodes(self, book_id: str, nodes: List[NarrativeNode], structure: StoryStructure) -> None: ...

    @abstractmethod
    def get_nodes(self, book_id: str) -> List[NarrativeNode]: ...

    @abstractmethod
    def get_node(self, book_id: str, node_id: str) -> Optional[NarrativeNode]: ...

    @abstractmethod
    def get_structure(self, book_id: str) -> Optional[StoryStructure]: ...
```

### 4.2 模型定义

```python
# src/models/user.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: str
    username: str
    email: str
    password_hash: str
    profile: dict = {}
    created_at: datetime

# src/models/book.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Book(BaseModel):
    id: str
    user_id: str
    title: str
    nodes_file_path: str
    status: str = "pending"
    created_at: datetime
```

---

## 5. 实现层设计

### 5.1 文件结构

```
src/
├── models/
│   ├── __init__.py
│   ├── user.py           # User 模型
│   ├── book.py           # Book 模型
│   ├── narrative_node.py # NarrativeNode, StoryStructure
│   └── chunk.py          # Chunk 模型
├── services/
│   ├── __init__.py
│   ├── interfaces.py     # 服务接口定义
│   ├── user_service.py   # IUserService 实现
│   ├── book_service.py   # IBookService 实现
│   └── node_service.py   # INodeService 实现
├── storage/
│   ├── __init__.py
│   ├── database.py       # SQLite 连接管理
│   ├── json_storage.py   # JSON 文件读写
│   └── path_builder.py   # 路径构建工具
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py    # API 请求/响应模型
│   └── routes/
│       ├── __init__.py
│       ├── auth.py       # 认证相关路由
│       ├── users.py      # 用户路由
│       ├── books.py      # 书籍路由
│       └── nodes.py      # 节点路由
└── pipeline.py
```

### 5.2 依赖关系

```
API Routes
    ↓
Services (依赖接口，通过参数注入)
    ↓
Storage Layer (database.py, json_storage.py)
    ↓
SQLite / File System
```

---

## 6. API 路由设计

### 6.1 认证路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册用户 |
| POST | /api/auth/login | 登录 |
| POST | /api/auth/logout | 登出 |

### 6.2 用户路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users/me | 获取当前用户 |
| PATCH | /api/users/me | 更新个人资料 |

### 6.3 书籍路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/books | 获取用户的所有书籍 |
| POST | /api/books | 创建书籍 |
| GET | /api/books/{id} | 获取书籍详情 |
| DELETE | /api/books/{id} | 删除书籍 |

### 6.4 节点路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/books/{id}/nodes | 获取书籍所有节点 |
| GET | /api/books/{id}/nodes/{node_id} | 获取单个节点 |
| POST | /api/books/{id}/nodes | 保存节点（处理完成后） |
| GET | /api/books/{id}/structure | 获取故事结构 |

### 6.5 上传路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload | 上传书籍文件 |

---

## 7. 向量存储

ChromaDB 保持独立，继续使用：

```python
# src/storage/vector_store.py
class VectorStore:
    def __init__(self, persist_dir: str): ...
    def add_node(self, node: NarrativeNode, original_text: str, book_id: str): ...
    def search(self, query: str, book_id: str = None, n_results: int = 3): ...
```

---

## 8. 迁移计划

### Phase 1: 模型重构
1. 创建 `User`, `Book` 模型
2. 更新 `NarrativeNode`, `StoryStructure` 模型

### Phase 2: 存储层重构
1. 实现 `database.py` - SQLite 表创建
2. 实现 `json_storage.py` - JSON 文件读写
3. 实现 `path_builder.py` - 路径构建

### Phase 3: 服务层重构
1. 实现 `interfaces.py` - 接口定义
2. 实现 `user_service.py`
3. 实现 `book_service.py`
4. 实现 `node_service.py`

### Phase 4: API 层适配
1. 更新 API routes 使用新服务
2. 添加认证路由
3. 移除旧的数据库调用

---

## 9. 兼容性考虑

- 旧数据库 `story_summary.db` 可保留，通过脚本迁移数据
- 前端 API 尽量保持兼容，减少前端改动
