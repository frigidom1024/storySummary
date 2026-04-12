# FastAPI API 层设计

## 概述

为 storySummary 项目实现 FastAPI 应用层，提供 RESTful API 接口。

## 技术栈

- FastAPI
- python-jose（JWT）
- passlib（密码 hashing）
- python-multipart（CORS 中间件）

## 目录结构

```
src/api/
├── __init__.py
├── main.py          # FastAPI 应用入口
├── deps.py          # 依赖注入
├── routers/
│   ├── __init__.py
│   ├── auth.py      # /auth 路由
│   ├── users.py     # /users 路由
│   └── books.py     # /books + /books/{id}/nodes 路由
└── schemas/
    ├── __init__.py
    ├── auth.py      # Token/Register/Login 响应
    ├── user.py      # UserResponse
    └── book.py      # BookCreate/BookResponse/NodeResponse
```

## 认证设计

- JWT Bearer Token
- 有效期 7 天
- Header 格式: `Authorization: Bearer <token>`
- 注册时即返回 Token，无需额外激活步骤

## API 端点

### Auth 路由 `/auth`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 注册用户，返回 Token |
| `/auth/login` | POST | 登录，返回 Token |

**Register 请求体**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**Login 请求体**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应（Token）**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### Users 路由 `/users`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/users/me` | GET | 获取当前用户信息 |
| `/users/me` | PATCH | 更新个人资料 |

### Books 路由 `/books`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/books` | GET | 列出当前用户书籍 |
| `/books` | POST | 创建书籍 |
| `/books/{id}` | GET | 获取书籍详情 |
| `/books/{id}` | DELETE | 删除书籍（软删除） |

**Create Book 请求体**
```json
{
  "title": "string"
}
```

**Book 响应**
```json
{
  "id": "string",
  "user_id": "string",
  "title": "string",
  "status": "pending | processing | completed | failed",
  "nodes_file_path": "string",
  "created_at": "datetime"
}
```

### Nodes 路由 `/books/{book_id}/nodes`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/books/{id}/nodes` | GET | 获取书籍所有节点 |
| `/books/{id}/nodes` | POST | 保存节点到书籍 |

**Nodes 响应**
```json
{
  "book_id": "string",
  "structure": { ... },
  "nodes": [ ... ]
}
```

**Save Nodes 请求体**
```json
{
  "structure": { ... },
  "nodes": [ ... ]
}
```

## 错误处理

| 状态码 | 说明 |
|--------|------|
| 401 | 未认证 / Token 无效 |
| 403 | 无权访问他人资源 |
| 404 | 资源不存在 |
| 422 | 请求参数校验失败 |

## CORS 配置

- Allow all origins（`allow_origins=["*"]`）
- Allow credentials
- Allow all methods and headers

## 启动方式

```bash
uvicorn src.api.main:app --reload --port 8000
```

## 数据库依赖

- 复用现有的 `Database` 类（`src/storage/database.py`）
- 通过 `deps.py` 注入 service 实例
