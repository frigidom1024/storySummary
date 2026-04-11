# Database Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor backend storage to use SQLite for users/books + JSON files for nodes, with interface-based service design.

**Architecture:** Three-layer architecture - API Routes → Services → Storage. Services depend on interfaces, storage implementations injected via constructor.

**Tech Stack:** FastAPI, SQLite, Pydantic, ChromaDB

---

## Chunk 1: Model Refactoring

### Task 1: Create User and Book Models

**Files:**
- Create: `src/models/user.py`
- Create: `src/models/book.py`
- Modify: `src/models/__init__.py`

---

- [ ] **Step 1: Create src/models/user.py**

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: str
    password_hash: str
    profile: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Create src/models/book.py**

```python
from pydantic import BaseModel
from datetime import datetime


class Book(BaseModel):
    """Book index model"""
    id: str
    user_id: str
    title: str
    nodes_file_path: str
    status: str = "pending"  # pending | processing | completed | failed
    is_deleted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Update src/models/__init__.py**

```python
from .user import User
from .book import Book
from .narrative_node import NarrativeNode, StoryStructure, CharacterState, RelationshipStateChange
from .chunk import Chunk

__all__ = [
    "User",
    "Book",
    "NarrativeNode",
    "StoryStructure",
    "CharacterState",
    "RelationshipStateChange",
    "Chunk",
]
```

---

### Task 2: Update Existing Models

**Files:**
- Modify: `src/models/narrative_node.py` (ensure completeness)
- Modify: `src/models/chunk.py` (ensure completeness)
- Modify: `src/models/story_structure.py` (ensure completeness)

---

- [ ] **Step 1: Update src/models/narrative_node.py**

```python
from pydantic import BaseModel, Field
from typing import Optional


class CharacterState(BaseModel):
    """角色在该节点进入时的状态"""
    name: str
    state_before: str = ""


class RelationshipStateChange(BaseModel):
    """一对角色在该节点中的关系变化"""
    pair: str = ""
    from_state: str = ""
    to_state: str = ""


class NarrativeNode(BaseModel):
    id: str
    parent_chunk_id: str = ""
    beat_index: int = 0
    scene: str = ""
    location: str = ""
    scene_timing: str = ""
    characters: list[CharacterState] = Field(default_factory=list)
    situation: str = ""
    turning_point: str = ""
    emotional_arc: str = ""
    mood_tone: str = ""
    narrative_rhythm: str = ""
    discussion_prompts: list[str] = Field(default_factory=list)
    relationship_delta: list[RelationshipStateChange] = Field(default_factory=list)
    prev_node_id: str = ""
    narrative_role: str = ""
    timeline_order: int = 0
    timeline_anchor: str = ""
    is_time_jump: bool = False
    jump_direction: str = ""
    jump_label: str = ""
    thread_id: str = "main"
    thread_name: str = ""
    thread_prev_node_id: str = ""
    thread_next_node_id: str = ""
    branch_from_node: str = ""
    converges_to_node: str = ""
    is_convergence: bool = False

    def to_dict(self) -> dict:
        return self.model_dump()
```

- [ ] **Step 2: Update src/models/story_structure.py**

```python
from pydantic import BaseModel, Field


class StoryStructure(BaseModel):
    linear_mainline: list[str] = Field(default_factory=list)
    opening: list[str] = Field(default_factory=list)
    rising: list[str] = Field(default_factory=list)
    climax: list[str] = Field(default_factory=list)
    ending: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()
```

- [ ] **Step 3: Update src/models/chunk.py**

```python
from pydantic import BaseModel
from typing import Optional


class Chunk(BaseModel):
    id: str
    text: str
    chapter: Optional[str] = None
    order: int = 0
```

---

## Chunk 2: Storage Layer

### Task 3: Create PathBuilder

**Files:**
- Create: `src/storage/path_builder.py`

---

- [ ] **Step 1: Create src/storage/path_builder.py**

```python
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
```

---

### Task 4: Create JsonStorage

**Files:**
- Create: `src/storage/json_storage.py`

---

- [ ] **Step 1: Create src/storage/json_storage.py**

```python
import json
import tempfile
import os
from pathlib import Path
from typing import Any


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
```

---

### Task 5: Refactor Database

**Files:**
- Modify: `src/storage/database.py` (replace with new implementation)

---

- [ ] **Step 1: Rewrite src/storage/database.py**

```python
import sqlite3
from typing import List, Optional
from src.models.user import User
from src.models.book import Book


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=1) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            # users 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    profile TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # books 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    nodes_file_path TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id)")

    # === Users ===

    def create_user(self, user: User) -> None:
        """创建用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO users (id, username, email, password_hash, profile, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user.id, user.username, user.email, user.password_hash,
                 str(user.profile), user.created_at)
            )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash, profile, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            if row:
                import json
                return User(
                    id=row[0], username=row[1], email=row[2],
                    password_hash=row[3], profile=json.loads(row[4]), created_at=row[5]
                )
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash, profile, created_at FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            if row:
                import json
                return User(
                    id=row[0], username=row[1], email=row[2],
                    password_hash=row[3], profile=json.loads(row[4]), created_at=row[5]
                )
            return None

    def update_user_profile(self, user_id: str, profile: dict) -> None:
        """更新用户资料"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET profile = ? WHERE id = ?",
                (json.dumps(profile), user_id)
            )

    # === Books ===

    def create_book(self, book: Book) -> None:
        """创建书籍"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO books (id, user_id, title, nodes_file_path, status, is_deleted, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (book.id, book.user_id, book.title, book.nodes_file_path,
                 book.status, int(book.is_deleted), book.created_at)
            )

    def get_book(self, book_id: str) -> Optional[Book]:
        """获取书籍"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT id, user_id, title, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE id = ? AND is_deleted = 0""",
                (book_id,)
            ).fetchone()
            if row:
                return Book(
                    id=row[0], user_id=row[1], title=row[2],
                    nodes_file_path=row[3], status=row[4],
                    is_deleted=bool(row[5]), created_at=row[6]
                )
            return None

    def get_books_for_user(self, user_id: str) -> List[Book]:
        """获取用户的所有书籍"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT id, user_id, title, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE user_id = ? AND is_deleted = 0 ORDER BY created_at DESC""",
                (user_id,)
            ).fetchall()
            return [
                Book(
                    id=r[0], user_id=r[1], title=r[2],
                    nodes_file_path=r[3], status=r[4],
                    is_deleted=bool(r[5]), created_at=r[6]
                )
                for r in rows
            ]

    def update_book_status(self, book_id: str, status: str) -> None:
        """更新书籍状态"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE books SET status = ? WHERE id = ?",
                (status, book_id)
            )

    def soft_delete_book(self, book_id: str) -> None:
        """软删除书籍"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE books SET is_deleted = 1 WHERE id = ?",
                (book_id,)
            )
```

---

## Chunk 3: Service Layer

### Task 6: Create Service Interfaces

**Files:**
- Create: `src/services/__init__.py`
- Create: `src/services/interfaces.py`

---

- [ ] **Step 1: Create src/services/interfaces.py**

```python
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

- [ ] **Step 2: Create src/services/__init__.py**

```python
from .interfaces import IUserService, IBookService, INodeService
from .user_service import UserService
from .book_service import BookService
from .node_service import NodeService

__all__ = [
    "IUserService",
    "IBookService",
    "INodeService",
    "UserService",
    "BookService",
    "NodeService",
]
```

---

### Task 7: Implement UserService

**Files:**
- Create: `src/services/user_service.py`

---

- [ ] **Step 1: Create src/services/user_service.py**

```python
import uuid
import hashlib
from datetime import datetime
from typing import Optional
from src.models.user import User
from src.services.interfaces import IUserService
from src.storage.database import Database


class UserService(IUserService):
    def __init__(self, db: Database):
        self.db = db

    def create_user(self, username: str, email: str, password: str) -> User:
        """创建用户"""
        password_hash = self._hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            profile={},
            created_at=datetime.now()
        )
        self.db.create_user(user)
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.get_user_by_username(username)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户"""
        user = self.db.get_user_by_username(username)
        if user and self._verify_password(password, user.password_hash):
            return user
        return None

    def update_profile(self, user_id: str, profile: dict) -> User:
        """更新用户资料"""
        self.db.update_user_profile(user_id, profile)
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        return user

    def _hash_password(self, password: str) -> str:
        """简单哈希密码（生产环境应使用 bcrypt）"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == password_hash
```

---

### Task 8: Implement BookService

**Files:**
- Create: `src/services/book_service.py`

---

- [ ] **Step 1: Create src/services/book_service.py**

```python
import uuid
from datetime import datetime
from typing import List, Optional
from src.models.book import Book
from src.services.interfaces import IBookService
from src.storage.database import Database
from src.storage.path_builder import PathBuilder


class BookService(IBookService):
    def __init__(self, db: Database, path_builder: PathBuilder):
        self.db = db
        self.path_builder = path_builder

    def create_book(self, user_id: str, title: str) -> Book:
        """创建书籍"""
        book_id = str(uuid.uuid4())
        nodes_file_path = self.path_builder.build_nodes_file(user_id, book_id)
        book = Book(
            id=book_id,
            user_id=user_id,
            title=title,
            nodes_file_path=nodes_file_path,
            status="pending",
            is_deleted=False,
            created_at=datetime.now()
        )
        self.db.create_book(book)
        return book

    def get_book(self, book_id: str) -> Optional[Book]:
        return self.db.get_book(book_id)

    def get_books_for_user(self, user_id: str) -> List[Book]:
        return self.db.get_books_for_user(user_id)

    def update_book_status(self, book_id: str, status: str) -> Book:
        """更新书籍状态"""
        self.db.update_book_status(book_id, status)
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        return book

    def delete_book(self, book_id: str) -> None:
        """软删除书籍"""
        self.db.soft_delete_book(book_id)
```

---

### Task 9: Implement NodeService

**Files:**
- Create: `src/services/node_service.py`

---

- [ ] **Step 1: Create src/services/node_service.py**

```python
from typing import List, Optional
from src.models.narrative_node import NarrativeNode, StoryStructure
from src.services.interfaces import INodeService
from src.storage.database import Database
from src.storage.json_storage import JsonStorage


class NodeService(INodeService):
    def __init__(self, db: Database, json_storage: JsonStorage):
        self.db = db
        self.json_storage = json_storage

    def save_nodes(self, book_id: str, nodes: List[NarrativeNode], structure: StoryStructure) -> None:
        """保存节点到 JSON 文件"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        data = {
            "book_id": book_id,
            "nodes": [node.model_dump() for node in nodes],
            "structure": structure.model_dump()
        }
        self.json_storage.write(book.nodes_file_path, data)

    def get_nodes(self, book_id: str) -> List[NarrativeNode]:
        """获取书籍所有节点"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        try:
            data = self.json_storage.read(book.nodes_file_path)
        except FileNotFoundError:
            return []

        return [NarrativeNode.model_validate(n) for n in data.get("nodes", [])]

    def get_node(self, book_id: str, node_id: str) -> Optional[NarrativeNode]:
        """获取单个节点"""
        nodes = self.get_nodes(book_id)
        for node in nodes:
            if node.id == node_id:
                return node
        return None

    def get_structure(self, book_id: str) -> Optional[StoryStructure]:
        """获取故事结构"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        try:
            data = self.json_storage.read(book.nodes_file_path)
        except FileNotFoundError:
            return None

        if "structure" in data:
            return StoryStructure.model_validate(data["structure"])
        return None
```

---

## Chunk 4: API Layer

### Task 10: Create API Schemas

**Files:**
- Create: `src/api/models/schemas.py`

---

- [ ] **Step 1: Create src/api/models/schemas.py**

```python
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    username: str


# User
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    profile: dict
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    profile: dict


# Book
class CreateBookRequest(BaseModel):
    title: str


class BookResponse(BaseModel):
    id: str
    user_id: str
    title: str
    status: str
    node_count: int = 0
    created_at: datetime


# Node
class NodeResponse(BaseModel):
    id: str
    scene: str
    location: str
    narrative_role: str
    thread_id: str
    timeline_order: int


class StructureResponse(BaseModel):
    opening: List[str]
    rising: List[str]
    climax: List[str]
    ending: List[str]
```

---

### Task 11: Create Auth Routes

**Files:**
- Create: `src/api/routes/auth.py`

---

- [ ] **Step 1: Create src/api/routes/auth.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from src.api.models.schemas import RegisterRequest, LoginRequest, AuthResponse
from src.services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_user_service() -> UserService:
    from src.api.main import user_service
    return user_service


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, service: UserService = Depends(get_user_service)):
    # 检查用户名是否存在
    if service.get_user_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    user = service.create_user(request.username, request.email, request.password)
    return AuthResponse(user_id=user.id, username=user.username)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, service: UserService = Depends(get_user_service)):
    user = service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(user_id=user.id, username=user.username)
```

---

### Task 12: Update API Routes to Use New Services

**Files:**
- Modify: `src/api/main.py`
- Modify: `src/api/routes/books.py`

---

- [ ] **Step 1: Update src/api/main.py**

```python
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import auth, books, upload
from src.storage.database import Database
from src.storage.path_builder import PathBuilder
from src.storage.json_storage import JsonStorage
from src.services.user_service import UserService
from src.services.book_service import BookService
from src.services.node_service import NodeService

DB_PATH = os.getenv("DB_PATH", "data/story_summary.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    data_dir = os.path.dirname(DB_PATH)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    # 初始化存储层
    db = Database(DB_PATH)
    path_builder = PathBuilder(os.path.dirname(DB_PATH))
    json_storage = JsonStorage()

    # 初始化服务层
    app.state.user_service = UserService(db)
    app.state.book_service = BookService(db, path_builder)
    app.state.node_service = NodeService(db, json_storage)

    yield
    # Shutdown


app = FastAPI(
    title="Story Summary API",
    description="API for uploading books and retrieving story summaries",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(upload.router)


@app.get("/")
async def root():
    return {"message": "Story Summary API", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# 全局服务访问
user_service: UserService = None
book_service: BookService = None
node_service: NodeService = None
```

- [ ] **Step 2: Update src/api/routes/books.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from src.api.models.schemas import BookResponse, CreateBookRequest
from src.services.book_service import BookService
from src.services.node_service import NodeService

router = APIRouter(prefix="/api/books", tags=["books"])


def get_book_service() -> BookService:
    from src.api.main import book_service
    return book_service


def get_node_service() -> NodeService:
    from src.api.main import node_service
    return node_service


@router.get("", response_model=List[BookResponse])
async def get_books(
    user_id: str = "default-user",
    book_service: BookService = Depends(get_book_service),
    node_service: NodeService = Depends(get_node_service)
):
    books = book_service.get_books_for_user(user_id)
    result = []
    for book in books:
        try:
            nodes = node_service.get_nodes(book.id)
            node_count = len(nodes)
        except:
            node_count = 0
        result.append(BookResponse(
            id=book.id,
            user_id=book.user_id,
            title=book.title,
            status=book.status,
            node_count=node_count,
            created_at=book.created_at
        ))
    return result


@router.post("", response_model=BookResponse)
async def create_book(
    request: CreateBookRequest,
    user_id: str = "default-user",
    book_service: BookService = Depends(get_book_service)
):
    book = book_service.create_book(user_id, request.title)
    return BookResponse(
        id=book.id,
        user_id=book.user_id,
        title=book.title,
        status=book.status,
        node_count=0,
        created_at=book.created_at
    )


@router.get("/{book_id}")
async def get_book(
    book_id: str,
    book_service: BookService = Depends(get_book_service),
    node_service: NodeService = Depends(get_node_service)
):
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        nodes = node_service.get_nodes(book_id)
        node_count = len(nodes)
    except:
        node_count = 0

    return BookResponse(
        id=book.id,
        user_id=book.user_id,
        title=book.title,
        status=book.status,
        node_count=node_count,
        created_at=book.created_at
    )


@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    book_service: BookService = Depends(get_book_service)
):
    book_service.delete_book(book_id)
    return {"message": "Book deleted"}


@router.get("/{book_id}/nodes")
async def get_book_nodes(
    book_id: str,
    node_service: NodeService = Depends(get_node_service)
):
    nodes = node_service.get_nodes(book_id)
    return [n.model_dump() for n in nodes]


@router.get("/{book_id}/structure")
async def get_book_structure(
    book_id: str,
    node_service: NodeService = Depends(get_node_service)
):
    structure = node_service.get_structure(book_id)
    if not structure:
        raise HTTPException(status_code=404, detail="Structure not found")
    return structure.model_dump()
```

---

## Summary

**Files Created/Modified:**

```
src/models/
├── __init__.py          # Updated
├── user.py              # Created
├── book.py              # Created
├── narrative_node.py    # Updated
├── chunk.py             # Updated
└── story_structure.py   # Updated

src/storage/
├── database.py          # Rewritten
├── json_storage.py      # Created
└── path_builder.py      # Created

src/services/
├── __init__.py          # Created
├── interfaces.py         # Created
├── user_service.py      # Created
├── book_service.py      # Created
└── node_service.py      # Created

src/api/
├── main.py              # Updated
├── models/
│   └── schemas.py       # Created
└── routes/
    ├── auth.py          # Created
    └── books.py         # Updated
```

**Run Commands:**
```bash
cd D:/project/storySummary
# 运行前需要先备份旧数据
python -m pytest tests/  # 测试
```

**Migration Note:**
- 旧数据库 `story_summary.db` 需要迁移脚本（Phase 4）
- 当前实现使用新的表结构
