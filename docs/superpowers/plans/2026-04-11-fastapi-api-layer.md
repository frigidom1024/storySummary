# FastAPI API 层实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 storySummary 项目实现 FastAPI API 层，提供用户认证、书籍管理和节点读写接口

**Architecture:** 使用 FastAPI + JWT 实现 RESTful API，依赖注入复用现有 service 层，CORS 支持跨域访问

**Tech Stack:** FastAPI, python-jose, passlib, python-multipart

---

## Chunk 1: 项目依赖和配置

**Files:**
- Create: `src/api/__init__.py`
- Modify: `requirements.txt` 或 `pyproject.toml`

- [ ] **Step 1: 检查现有依赖配置**

Run: `cat requirements.txt 2>/dev/null || cat pyproject.toml 2>/dev/null || echo "no deps file"`
Expected: 查看现有依赖

- [ ] **Step 2: 添加 FastAPI 依赖到 requirements.txt**

```txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
```

- [ ] **Step 3: 创建 src/api/__init__.py**

```python
"""FastAPI API 层"""
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/api/__init__.py
git commit -m "feat: add FastAPI dependencies and api package"
```

---

## Chunk 2: Pydantic Schemas

**Files:**
- Create: `src/api/schemas/__init__.py`
- Create: `src/api/schemas/auth.py`
- Create: `src/api/schemas/user.py`
- Create: `src/api/schemas/book.py`

- [ ] **Step 1: 创建 src/api/schemas/__init__.py**

```python
"""API 请求/响应模型"""
from src.api.schemas.auth import Token, RegisterRequest, LoginRequest
from src.api.schemas.user import UserResponse
from src.api.schemas.book import BookCreate, BookResponse, NodesResponse

__all__ = [
    "Token",
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "BookCreate",
    "BookResponse",
    "NodesResponse",
]
```

- [ ] **Step 2: 创建 src/api/schemas/auth.py**

```python
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
```

- [ ] **Step 3: 创建 src/api/schemas/user.py**

```python
from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    profile: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 4: 创建 src/api/schemas/book.py**

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Any


class BookCreate(BaseModel):
    title: str


class BookResponse(BaseModel):
    id: str
    user_id: str
    title: str
    status: str
    nodes_file_path: str
    created_at: datetime

    class Config:
        from_attributes = True


class NodesResponse(BaseModel):
    book_id: str
    structure: Optional[dict] = None
    nodes: List[dict] = []


class SaveNodesRequest(BaseModel):
    structure: Optional[dict] = None
    nodes: List[dict] = []
```

- [ ] **Step 5: Commit**

```bash
git add src/api/schemas/
git commit -m "feat: add Pydantic schemas for API requests/responses"
```

---

## Chunk 3: 依赖注入 (deps.py)

**Files:**
- Create: `src/api/deps.py`

- [ ] **Step 1: 创建 src/api/deps.py**

```python
from typing import Generator
from src.storage.database import Database
from src.storage.path_builder import PathBuilder
from src.services.user_service import UserService
from src.services.book_service import BookService
from src.services.node_service import NodeService

# 全局实例（单例模式）
_db = None
_path_builder = None
_user_service = None
_book_service = None
_node_service = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database("data/story_summary.db")
    return _db


def get_path_builder() -> PathBuilder:
    global _path_builder
    if _path_builder is None:
        _path_builder = PathBuilder("data")
    return _path_builder


def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService(get_database())
    return _user_service


def get_book_service() -> BookService:
    global _book_service
    if _book_service is None:
        _book_service = BookService(get_database(), get_path_builder())
    return _book_service


def get_node_service() -> NodeService:
    global _node_service
    if _node_service is None:
        from src.storage.json_storage import JsonStorage
        _node_service = NodeService(JsonStorage())
    return _node_service
```

- [ ] **Step 2: Commit**

```bash
git add src/api/deps.py
git commit -m "feat: add dependency injection for services"
```

---

## Chunk 4: JWT 认证工具

**Files:**
- Create: `src/api/security.py`

- [ ] **Step 1: 创建 src/api/security.py**

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key-change-in-production"  # TODO: 从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

- [ ] **Step 2: Commit**

```bash
git add src/api/security.py
git commit -m "feat: add JWT security utilities"
```

---

## Chunk 5: 路由 - Auth

**Files:**
- Create: `src/api/routers/__init__.py`
- Create: `src/api/routers/auth.py`

- [ ] **Step 1: 创建 src/api/routers/__init__.py**

```python
"""API 路由"""
```

- [ ] **Step 2: 创建 src/api/routers/auth.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas.auth import Token, RegisterRequest, LoginRequest
from src.api.schemas.user import UserResponse
from src.api.security import create_access_token, get_password_hash, verify_password
from src.api.deps import get_user_service
from src.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(request: RegisterRequest, user_service: UserService = Depends(get_user_service)):
    # 检查用户名是否存在
    existing = user_service.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户
    user = user_service.create_user(
        username=request.username,
        email=request.email,
        password=request.password
    )

    # 生成 Token
    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
def login(request: LoginRequest, user_service: UserService = Depends(get_user_service)):
    user = user_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token)
```

- [ ] **Step 3: Commit**

```bash
git add src/api/routers/__init__.py src/api/routers/auth.py
git commit -m "feat: add auth router with register/login endpoints"
```

---

## Chunk 6: 路由 - Users

**Files:**
- Create: `src/api/routers/users.py`

- [ ] **Step 1: 创建 src/api/routers/users.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas.user import UserResponse
from src.api.security import decode_token
from src.api.deps import get_user_service
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_current_user(token: str = Depends(lambda: None), user_service: UserService = Depends(get_user_service)):
    """从 Token 获取当前用户（暂未实现认证中间件）"""
    # TODO: 实现完整的 Bearer Token 认证
    return None


@router.get("/me", response_model=UserResponse)
def get_me(user_service: UserService = Depends(get_user_service)):
    """获取当前用户信息"""
    # TODO: 需要实现完整的认证中间件
    raise HTTPException(status_code=501, detail="Auth middleware not yet implemented")


@router.patch("/me", response_model=UserResponse)
def update_me(profile: dict, user_service: UserService = Depends(get_user_service)):
    """更新当前用户资料"""
    # TODO: 需要实现完整的认证中间件
    raise HTTPException(status_code=501, detail="Auth middleware not yet implemented")
```

- [ ] **Step 2: Commit**

```bash
git add src/api/routers/users.py
git commit -m "feat: add users router skeleton"
```

---

## Chunk 7: 路由 - Books

**Files:**
- Create: `src/api/routers/books.py`

- [ ] **Step 1: 创建 src/api/routers/books.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.api.schemas.book import BookCreate, BookResponse, NodesResponse, SaveNodesRequest
from src.api.deps import get_book_service, get_node_service
from src.services.book_service import BookService
from src.services.node_service import NodeService

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=List[BookResponse])
def list_books(book_service: BookService = Depends(get_book_service)):
    """列出所有书籍（暂不支持多用户）"""
    # TODO: 实现完整认证后需按 user_id 过滤
    raise HTTPException(status_code=501, detail="Auth required")


@router.post("", response_model=BookResponse)
def create_book(request: BookCreate, book_service: BookService = Depends(get_book_service)):
    """创建书籍"""
    # TODO: 实现完整认证后需传入 user_id
    raise HTTPException(status_code=501, detail="Auth required")


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: str, book_service: BookService = Depends(get_book_service)):
    """获取书籍详情"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/{book_id}")
def delete_book(book_id: str, book_service: BookService = Depends(get_book_service)):
    """删除书籍"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book_service.delete_book(book_id)
    return {"message": "Book deleted"}


@router.get("/{book_id}/nodes", response_model=NodesResponse)
def get_nodes(book_id: str, node_service: NodeService = Depends(get_node_service)):
    """获取书籍的节点"""
    nodes = node_service.get_nodes(book_id)
    return NodesResponse(book_id=book_id, nodes=[n.to_dict() for n in nodes])


@router.post("/{book_id}/nodes")
def save_nodes(
    book_id: str,
    request: SaveNodesRequest,
    node_service: NodeService = Depends(get_node_service),
    book_service: BookService = Depends(get_book_service)
):
    """保存节点到书籍"""
    # 验证书籍存在
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # TODO: 将 dict 转换为 NarrativeNode 对象
    # TODO: 调用 node_service.save_nodes
    return {"message": "Nodes saved"}
```

- [ ] **Step 2: Commit**

```bash
git add src/api/routers/books.py
git commit -m "feat: add books router skeleton"
```

---

## Chunk 8: FastAPI Main 应用入口

**Files:**
- Create: `src/api/main.py`

- [ ] **Step 1: 创建 src/api/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import auth, users, books

app = FastAPI(
    title="Story Summary API",
    description="API for story summarization and narrative analysis",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)


@app.get("/")
def root():
    return {"message": "Story Summary API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
```

- [ ] **Step 2: Commit**

```bash
git add src/api/main.py
git commit -m "feat: add FastAPI main application entry point"
```

---

## Chunk 9: 完善认证中间件和路由

**Files:**
- Modify: `src/api/deps.py`
- Modify: `src/api/routers/users.py`
- Modify: `src/api/routers/books.py`

- [ ] **Step 1: 更新 deps.py 添加认证依赖**

```python
from fastapi import Header, HTTPException, Depends
from typing import Optional

# ... 现有代码 ...

def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """从 Authorization header 获取当前用户 ID"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    token = authorization[7:]  # 去掉 "Bearer " 前缀
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return user_id
```

- [ ] **Step 2: 更新 users.py 实现完整认证**

```python
from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas.user import UserResponse
from src.api.deps import get_user_service, get_current_user_id
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """获取当前用户信息"""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
def update_me(
    profile: dict,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """更新当前用户资料"""
    user = user_service.update_profile(user_id, profile)
    return user
```

- [ ] **Step 3: 更新 books.py 实现完整认证**

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.api.schemas.book import BookCreate, BookResponse, NodesResponse, SaveNodesRequest
from src.api.deps import get_book_service, get_node_service, get_current_user_id
from src.services.book_service import BookService
from src.services.node_service import NodeService

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=List[BookResponse])
def list_books(
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """列出当前用户的所有书籍"""
    return book_service.get_books_for_user(user_id)


@router.post("", response_model=BookResponse)
def create_book(
    request: BookCreate,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """创建书籍"""
    return book_service.create_book(user_id, request.title)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """获取书籍详情"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this book")
    return book


@router.delete("/{book_id}")
def delete_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """删除书籍"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this book")
    book_service.delete_book(book_id)
    return {"message": "Book deleted"}


@router.get("/{book_id}/nodes", response_model=NodesResponse)
def get_nodes(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service),
    node_service: NodeService = Depends(get_node_service)
):
    """获取书籍的节点"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this book")

    nodes = node_service.get_nodes(book_id)
    return NodesResponse(book_id=book_id, nodes=[n.to_dict() for n in nodes])


@router.post("/{book_id}/nodes")
def save_nodes(
    book_id: str,
    request: SaveNodesRequest,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service),
    node_service: NodeService = Depends(get_node_service)
):
    """保存节点到书籍"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this book")

    # 更新书籍状态为 processing
    book_service.update_book_status(book_id, "processing")

    # TODO: 将 dict 转换为 NarrativeNode 对象后保存
    return {"message": "Nodes saved", "book_id": book_id}
```

- [ ] **Step 4: Commit**

```bash
git add src/api/deps.py src/api/routers/users.py src/api/routers/books.py
git commit -m "feat: implement complete JWT auth and protected routes"
```

---

## Chunk 10: NodeService 实现检查

**Files:**
- Read: `src/services/node_service.py`

- [ ] **Step 1: 检查 NodeService 是否已实现**

Run: `cat src/services/node_service.py`
Expected: 查看 INodeService 实现

- [ ] **Step 2: 如需要，更新 NodeService 的 save_nodes 实现**

（根据实际情况决定是否需要修改）
