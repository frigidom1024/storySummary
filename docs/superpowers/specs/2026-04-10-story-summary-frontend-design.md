# Story Summary 前端设计文档

## 1. 概述与目标

**项目名称：** Story Summary Web
**项目类型：** 单页应用 (SPA)
**核心目标：** 提供小说叙事节点的可视化浏览界面

**已有能力：**
- FastAPI 后端（上传、节点生成、存储）
- 已实现的 API 端点

**本项目范围：**
- Vue3 + Vite 前端应用
- 节点时间线浏览
- 书籍上传与进度展示

---

## 2. 技术栈

| 层级 | 技术选型 |
|------|---------|
| 框架 | Vue 3 (Composition API) |
| 构建 | Vite |
| 路由 | Vue Router 4 |
| 状态 | Pinia |
| HTTP | Axios |
| 样式 | 原生 CSS + CSS Variables |

---

## 3. 页面结构

### 3.1 路由设计

```
/                   → 书籍列表页
/books/:id         → 书籍详情页（节点时间线）
```

### 3.2 页面层级

```
App.vue
├── Header (应用标题)
├── RouterView
│   ├── HomeView (书籍列表)
│   │   ├── UploadArea (上传区)
│   │   └── BookList (书籍卡片列表)
│   └── BookDetailView (书籍详情)
│       ├── BookHeader (书籍信息)
│       ├── FilterBar (筛选栏)
│       └── TimelineView (时间线)
│           └── TimelineNode (节点卡片)
│               └── NodeDetail (节点详情弹窗)
```

---

## 4. 组件设计

### 4.1 HomeView - 书籍列表页

**功能：**
- 显示所有已上传书籍
- 文件上传区域
- 显示上传进度

**数据来源：**
- `GET /api/books`

**布局：**
- 顶部：应用标题 + 上传按钮
- 中部：书籍卡片网格 (2-3列)

### 4.2 UploadArea - 上传区域

**功能：**
- 拖拽上传 TXT/EPUB 文件
- 显示上传进度
- 显示处理状态

**交互：**
- 拖拽文件到上传区 → 自动上传
- 或点击选择文件
- 实时显示 `progress` 和 `status`

**数据来源：**
- `POST /api/upload`
- `GET /api/upload/{book_id}/status`

### 4.3 BookCard - 书籍卡片

**显示信息：**
- 书名
- 节点数量
- 创建时间

**交互：**
- 点击跳转至 `/books/{id}`

### 4.4 BookDetailView - 书籍详情页

**功能：**
- 展示单本书的所有叙事节点
- 时间线视图

**数据来源：**
- `GET /api/books/{id}`
- `GET /api/books/{id}/nodes`
- `GET /api/books/{id}/structure`

### 4.5 FilterBar - 筛选栏

**功能：**
- 搜索节点（根据 situation、scene 等字段）
- 筛选节点类型（opening/rising/climax/ending）
- 筛选时间锚点（timeline_anchor）

**交互：**
- 输入搜索 → 实时过滤时间线节点

### 4.6 TimelineView - 时间线视图

**布局：**
- 纵向时间线
- 中间留白，左右交替排列节点卡片（可选，简单版本单侧排列）
- 时间跳跃处显示标记

**节点卡片内容：**
```
┌─────────────────────────────┐
│ [opening/rising/climax]     │  ← narrative_role 标签
│ 第三章：重逢                  │  ← 节点ID或场景名
│ ---------------------------- │
│ 📍 青岛路旧书店               │  ← location
│ ⏰ 午后                      │  ← scene_timing
│ 👤 陈屿、沈昭                │  ← characters
│ 💭 情绪：从疏离到试探          │  ← emotional_arc
└─────────────────────────────┘
```

**时间跳跃标记：**
- `is_time_jump = true` 时，显示跳跃方向标签（如 "插叙"、"倒叙"）

### 4.7 NodeDetail - 节点详情弹窗

**触发：**
- 点击节点卡片

**显示全部字段：**
- situation（核心情境）
- turning_point（转折点）
- emotional_arc（情绪弧）
- mood_tone（氛围）
- narrative_rhythm（节奏）
- discussion_prompts（讨论锚点）
- relationship_delta（关系变化）
- characters（角色状态列表）

---

## 5. 数据模型

### 5.1 NarrativeNode 展示字段

| 字段 | 说明 | 展示位置 |
|------|------|---------|
| id | 节点ID | 卡片头部 |
| narrative_role | opening/rising/climax/ending | 标签 |
| scene | 完整场景描述 | 卡片标题 |
| location | 简化地点 | 卡片内容 |
| scene_timing | 时间段 | 卡片内容 |
| characters | 角色列表 | 卡片内容 |
| emotional_arc | 情绪弧 | 卡片内容 |
| is_time_jump | 是否时间跳跃 | 标记 |
| jump_label | 跳跃类型 | 标记 |

### 5.2 筛选数据结构

```typescript
interface NodeFilter {
  search: string;        // 搜索关键词
  narrativeRole?: string; // opening/rising/climax/ending
  timelineAnchor?: string;// 时间锚点
}
```

---

## 6. API 调用层

```typescript
// api/index.ts
GET    /api/books
POST   /api/upload
GET    /api/upload/{book_id}/status
GET    /api/books/{book_id}
GET    /api/books/{book_id}/nodes
GET    /api/books/{book_id}/structure
DELETE /api/books/{book_id}
```

---

## 7. 项目结构

```
web/
├── index.html
├── vite.config.ts
├── package.json
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   └── books.ts
│   ├── api/
│   │   └── index.ts
│   ├── views/
│   │   ├── HomeView.vue
│   │   └── BookDetailView.vue
│   ├── components/
│   │   ├── Header.vue
│   │   ├── UploadArea.vue
│   │   ├── BookCard.vue
│   │   ├── FilterBar.vue
│   │   ├── TimelineView.vue
│   │   ├── TimelineNode.vue
│   │   └── NodeDetail.vue
│   └── styles/
│       └── variables.css
```

---

## 8. 样式规范

### 8.1 CSS Variables

```css
:root {
  --color-bg: #f8f9fa;
  --color-surface: #ffffff;
  --color-primary: #3b82f6;
  --color-text: #1f2937;
  --color-text-secondary: #6b7280;
  --color-border: #e5e7eb;
  --color-role-opening: #10b981;
  --color-role-rising: #f59e0b;
  --color-role-climax: #ef4444;
  --color-role-ending: #8b5cf6;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
}
```

### 8.2 typography

- 主字体：system-ui, -apple-system, sans-serif
- 叙事角色标签：等宽字体 or 粗体

---

## 9. 非功能需求

- 响应式设计（支持 1024px+ 宽度）
- 加载状态显示（骨架屏或 spinner）
- 错误提示（上传失败、网络错误）
- 空状态（无书籍、无节点）

---

## 10. 优先级

**P0（必须）：**
- 书籍列表展示
- 文件上传
- 节点时间线浏览
- 节点详情查看

**P1（期望）：**
- 节点搜索/筛选
- 上传进度显示
- 时间跳跃标记

**P2（可选）：**
- 节点关系连线
- 导出功能
