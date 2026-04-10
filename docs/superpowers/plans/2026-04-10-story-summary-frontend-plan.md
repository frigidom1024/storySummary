# Story Summary Frontend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Vue3 + Vite frontend application for browsing novel narrative nodes with multi-thread timeline visualization.

**Architecture:** Vue 3 SPA with Vue Router 4 for routing, Pinia for state management, Axios for API calls. CSS Variables for theming. Components organized by feature.

**Tech Stack:** Vue 3 (Composition API), Vite, Vue Router 4, Pinia, Axios

---

## Chunk 1: Project Scaffolding

### Task 1: Initialize Vite + Vue3 Project

**Files:**
- Create: `web/index.html`
- Create: `web/vite.config.ts`
- Create: `web/package.json`
- Create: `web/src/main.ts`
- Create: `web/src/App.vue`
- Create: `web/src/router/index.ts`
- Create: `web/src/styles/variables.css`

---

- [ ] **Step 1: Create web/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Story Summary</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 2: Create web/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create web/package.json**

```json
{
  "name": "story-summary-web",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0"
  }
}
```

- [ ] **Step 4: Create web/src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/variables.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 5: Create web/src/App.vue**

```vue
<template>
  <div class="app">
    <Header />
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import Header from './components/Header.vue'
</script>

<style>
.app {
  min-height: 100vh;
  background: var(--color-bg);
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
}
</style>
```

- [ ] **Step 6: Create web/src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import BookDetailView from '../views/BookDetailView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/books/:id',
      name: 'book-detail',
      component: BookDetailView,
    },
  ],
})

export default router
```

- [ ] **Step 7: Create web/src/styles/variables.css**

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
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  color: var(--color-text);
  background: var(--color-bg);
}
```

---

### Task 2: Create API Layer

**Files:**
- Create: `web/src/api/index.ts`

---

- [ ] **Step 1: Create web/src/api/index.ts**

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export interface Book {
  id: string
  title: string
  node_count: number
  created_at: string
}

export interface CharacterState {
  name: string
  state_before: string
}

export interface RelationshipStateChange {
  pair: string
  from_state: string
  to_state: string
}

export interface NarrativeNode {
  id: string
  parent_chunk_id: string
  beat_index: number
  scene: string
  location: string
  scene_timing: string
  characters: CharacterState[]
  situation: string
  turning_point: string
  emotional_arc: string
  mood_tone: string
  narrative_rhythm: string
  discussion_prompts: string[]
  relationship_delta: RelationshipStateChange[]
  prev_node_id: string
  narrative_role: string
  timeline_order: number
  timeline_anchor: string
  is_time_jump: boolean
  jump_direction: string
  jump_label: string
  thread_id: string
  thread_name: string
  thread_prev_node_id: string
  thread_next_node_id: string
  branch_from_node: string
  converges_to_node: string
  is_convergence: boolean
}

export interface ProcessingStatus {
  book_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
}

export const booksApi = {
  getBooks: () => api.get<Book[]>('/books'),

  getBook: (bookId: string) => api.get<Book>(`/books/${bookId}`),

  getBookNodes: (bookId: string) => api.get<NarrativeNode[]>(`/books/${bookId}/nodes`),

  getBookStructure: (bookId: string) => api.get('/books/${bookId}/structure'),

  deleteBook: (bookId: string) => api.delete(`/books/${bookId}`),

  uploadBook: (file: File, userId: string = 'default-user') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId)
    return api.post<{ book_id: string; status: string; message: string }>('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  getUploadStatus: (bookId: string) => api.get<ProcessingStatus>(`/upload/${bookId}/status`),
}
```

---

## Chunk 2: Pinia Store

### Task 3: Create Books Store

**Files:**
- Create: `web/src/stores/books.ts`

---

- [ ] **Step 1: Create web/src/stores/books.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { booksApi, type Book, type NarrativeNode } from '../api'

export const useBooksStore = defineStore('books', () => {
  const books = ref<Book[]>([])
  const currentBook = ref<Book | null>(null)
  const nodes = ref<NarrativeNode[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const nodesByThread = computed(() => {
    const grouped: Record<string, NarrativeNode[]> = {}
    for (const node of nodes.value) {
      const threadId = node.thread_id || 'main'
      if (!grouped[threadId]) {
        grouped[threadId] = []
      }
      grouped[threadId].push(node)
    }
    // Sort each thread by timeline_order
    for (const threadId in grouped) {
      grouped[threadId].sort((a, b) => a.timeline_order - b.timeline_order)
    }
    return grouped
  })

  const threadIds = computed(() => Object.keys(nodesByThread.value))

  async function fetchBooks() {
    loading.value = true
    error.value = null
    try {
      const res = await booksApi.getBooks()
      books.value = res.data
    } catch (e) {
      error.value = 'Failed to fetch books'
    } finally {
      loading.value = false
    }
  }

  async function fetchBookNodes(bookId: string) {
    loading.value = true
    error.value = null
    try {
      const [bookRes, nodesRes] = await Promise.all([
        booksApi.getBook(bookId),
        booksApi.getBookNodes(bookId),
      ])
      currentBook.value = bookRes.data
      nodes.value = nodesRes.data
    } catch (e) {
      error.value = 'Failed to fetch book details'
    } finally {
      loading.value = false
    }
  }

  async function uploadBook(file: File) {
    const res = await booksApi.uploadBook(file)
    return res.data.book_id
  }

  function clearCurrentBook() {
    currentBook.value = null
    nodes.value = []
  }

  return {
    books,
    currentBook,
    nodes,
    loading,
    error,
    nodesByThread,
    threadIds,
    fetchBooks,
    fetchBookNodes,
    uploadBook,
    clearCurrentBook,
  }
})
```

---

## Chunk 3: Core Components

### Task 4: Header Component

**Files:**
- Create: `web/src/components/Header.vue`

---

- [ ] **Step 1: Create web/src/components/Header.vue**

```vue
<template>
  <header class="header">
    <div class="header-content">
      <h1 class="logo" @click="router.push('/')">Story Summary</h1>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 16px 24px;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
}

.logo {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  cursor: pointer;
}

.logo:hover {
  color: var(--color-primary);
}
</style>
```

---

### Task 5: BookCard & BookList Components

**Files:**
- Create: `web/src/components/BookCard.vue`
- Create: `web/src/components/BookList.vue`

---

- [ ] **Step 1: Create web/src/components/BookCard.vue**

```vue
<template>
  <div class="book-card" @click="onClick">
    <h3 class="book-title">{{ book.title }}</h3>
    <div class="book-meta">
      <span class="node-count">{{ book.node_count }} 节点</span>
      <span class="created-at">{{ formatDate(book.created_at) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Book } from '../api'

const props = defineProps<{ book: Book }>()
const router = useRouter()

function onClick() {
  router.push(`/books/${props.book.id}`)
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.book-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.book-card:hover {
  box-shadow: var(--shadow);
}

.book-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.book-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
</style>
```

- [ ] **Step 2: Create web/src/components/BookList.vue**

```vue
<template>
  <div class="book-list">
    <div v-if="books.length === 0" class="empty-state">
      暂无书籍，请上传
    </div>
    <div v-else class="book-grid">
      <BookCard v-for="book in books" :key="book.id" :book="book" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Book } from '../api'
import BookCard from './BookCard.vue'

defineProps<{ books: Book[] }>()
</script>

<style scoped>
.book-list {
  margin-top: 24px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--color-text-secondary);
}
</style>
```

---

### Task 6: UploadArea Component

**Files:**
- Create: `web/src/components/UploadArea.vue`

---

- [ ] **Step 1: Create web/src/components/UploadArea.vue**

```vue
<template>
  <div
    class="upload-area"
    :class="{ dragging: isDragging, uploading: uploading }"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".txt,.epub"
      @change="handleFileChange"
      style="display: none"
    />
    <div v-if="uploading" class="upload-progress">
      <div class="spinner"></div>
      <span>{{ statusMessage }}</span>
    </div>
    <div v-else class="upload-hint">
      <span class="upload-icon">+</span>
      <span>拖拽文件或点击上传 ( TXT / EPUB )</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useBooksStore } from '../stores/books'

const store = useBooksStore()
const fileInput = ref<HTMLInputElement>()
const isDragging = ref(false)
const uploading = ref(false)
const statusMessage = ref('')

function triggerFileInput() {
  fileInput.value?.click()
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) uploadFile(file)
}

function handleFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) uploadFile(file)
}

async function uploadFile(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['txt', 'epub'].includes(ext || '')) {
    alert('仅支持 TXT 和 EPUB 文件')
    return
  }

  uploading.value = true
  statusMessage.value = '上传中...'

  try {
    await store.uploadBook(file)
    statusMessage.value = '上传成功，处理中...'
    await store.fetchBooks()
    statusMessage.value = '完成'
  } catch (e) {
    statusMessage.value = '上传失败'
    alert('上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-area {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover,
.upload-area.dragging {
  border-color: var(--color-primary);
  background: rgba(59, 130, 246, 0.05);
}

.upload-area.uploading {
  cursor: default;
}

.upload-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
}

.upload-icon {
  font-size: 32px;
  color: var(--color-primary);
}

.upload-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
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
</style>
```

---

## Chunk 4: HomeView

### Task 7: HomeView Component

**Files:**
- Create: `web/src/views/HomeView.vue`

---

- [ ] **Step 1: Create web/src/views/HomeView.vue**

```vue
<template>
  <div class="home-view">
    <h2 class="page-title">我的书籍</h2>
    <UploadArea />
    <BookList :books="store.books" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useBooksStore } from '../stores/books'
import UploadArea from '../components/UploadArea.vue'
import BookList from '../components/BookList.vue'

const store = useBooksStore()

onMounted(() => {
  store.fetchBooks()
})
</script>

<style scoped>
.home-view {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
}
</style>
```

---

## Chunk 5: Detail Components

### Task 8: FilterBar Component

**Files:**
- Create: `web/src/components/FilterBar.vue`

---

- [ ] **Step 1: Create web/src/components/FilterBar.vue**

```vue
<template>
  <div class="filter-bar">
    <input
      v-model="localFilter.search"
      type="text"
      placeholder="搜索场景、情境..."
      class="search-input"
      @input="emitFilter"
    />
    <div class="role-filter">
      <label v-for="role in narrativeRoles" :key="role" class="role-chip">
        <input
          type="checkbox"
          :value="role"
          v-model="localFilter.narrativeRoles"
          @change="emitFilter"
        />
        <span :class="['role-label', `role-${role}`]">{{ role }}</span>
      </label>
    </div>
    <div class="thread-filter">
      <span class="filter-label">叙事线:</span>
      <label v-for="thread in threads" :key="thread" class="thread-chip">
        <input
          type="checkbox"
          :value="thread"
          v-model="localFilter.visibleThreads"
          @change="emitFilter"
        />
        <span>{{ thread }}</span>
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface NodeFilter {
  search: string
  narrativeRoles: string[]
  visibleThreads: string[]
}

const props = defineProps<{
  threads: string[]
  initialFilter?: NodeFilter
}>()

const emit = defineEmits<{
  filter: [filter: NodeFilter]
}>()

const narrativeRoles = ['opening', 'rising', 'climax', 'ending']

const localFilter = ref<NodeFilter>({
  search: '',
  narrativeRoles: [],
  visibleThreads: props.threads.length > 0 ? [...props.threads] : [],
  ...props.initialFilter,
})

watch(() => props.threads, (newThreads) => {
  if (newThreads.length > 0) {
    localFilter.value.visibleThreads = [...newThreads]
  }
})

function emitFilter() {
  emit('filter', { ...localFilter.value })
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  padding: 16px;
  background: var(--color-surface);
  border-radius: var(--radius);
  margin-bottom: 24px;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.role-filter,
.thread-filter {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.role-chip,
.thread-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.role-chip input,
.thread-chip input {
  display: none;
}

.role-label {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.role-chip input:checked + .role-label {
  opacity: 1;
}

.role-label.role-opening { background: var(--color-role-opening); color: white; }
.role-label.role-rising { background: var(--color-role-rising); color: white; }
.role-label.role-climax { background: var(--color-role-climax); color: white; }
.role-label.role-ending { background: var(--color-role-ending); color: white; }

.thread-chip span {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.thread-chip input:checked + span {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}
</style>
```

---

### Task 9: TimelineNode Component

**Files:**
- Create: `web/src/components/TimelineNode.vue`

---

- [ ] **Step 1: Create web/src/components/TimelineNode.vue**

```vue
<template>
  <div
    class="timeline-node"
    :class="[`role-${node.narrative_role}`, { 'has-jump': node.is_time_jump }]"
    @click="emit('click', node)"
  >
    <div class="node-header">
      <span class="role-tag" :class="`role-${node.narrative_role}`">
        {{ node.narrative_role }}
      </span>
      <span v-if="node.is_time_jump" class="jump-tag">
        {{ node.jump_direction === 'past' ? '插叙' : '预叙' }}
      </span>
    </div>
    <div class="node-scene">{{ node.scene || '未知场景' }}</div>
    <div class="node-meta">
      <span v-if="node.location">{{ node.location }}</span>
      <span v-if="node.scene_timing">{{ node.scene_timing }}</span>
    </div>
    <div class="node-characters">
      {{ characterNames }}
    </div>
    <div v-if="node.emotional_arc" class="node-emotion">
      {{ node.emotional_arc }}
    </div>
    <div v-if="node.timeline_anchor" class="node-anchor">
      {{ node.timeline_anchor }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NarrativeNode } from '../api'

const props = defineProps<{ node: NarrativeNode }>()
const emit = defineEmits<{ click: [node: NarrativeNode] }>()

const characterNames = computed(() =>
  props.node.characters?.map((c) => c.name).join('、') || ''
)
</script>

<style scoped>
.timeline-node {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
  min-width: 180px;
  max-width: 220px;
}

.timeline-node:hover {
  box-shadow: var(--shadow);
}

.node-header {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.role-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  color: white;
}

.role-opening { background: var(--color-role-opening); }
.role-rising { background: var(--color-role-rising); }
.role-climax { background: var(--color-role-climax); }
.role-ending { background: var(--color-role-ending); }

.jump-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  background: #9333ea;
  color: white;
}

.node-scene {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  line-height: 1.3;
}

.node-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.node-characters {
  font-size: 12px;
  color: var(--color-text);
  margin-bottom: 4px;
}

.node-emotion {
  font-size: 11px;
  color: var(--color-text-secondary);
  font-style: italic;
}

.node-anchor {
  margin-top: 6px;
  font-size: 11px;
  color: #9333ea;
  font-weight: 500;
}
</style>
```

---

### Task 10: NodeDetail Modal Component

**Files:**
- Create: `web/src/components/NodeDetail.vue`

---

- [ ] **Step 1: Create web/src/components/NodeDetail.vue**

```vue
<template>
  <Teleport to="body">
    <div v-if="node" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-content">
        <button class="close-btn" @click="emit('close')">x</button>
        <h2 class="modal-title">{{ node.scene }}</h2>

        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-row">
            <span class="label">ID:</span>
            <span>{{ node.id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">叙事角色:</span>
            <span class="role-tag" :class="`role-${node.narrative_role}`">
              {{ node.narrative_role }}
            </span>
          </div>
          <div class="detail-row">
            <span class="label">叙事线:</span>
            <span>{{ node.thread_name || node.thread_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">时间顺序:</span>
            <span>{{ node.timeline_order }}</span>
          </div>
          <div v-if="node.timeline_anchor" class="detail-row">
            <span class="label">时间锚点:</span>
            <span>{{ node.timeline_anchor }}</span>
          </div>
        </div>

        <div v-if="node.situation" class="detail-section">
          <h4>核心情境</h4>
          <p>{{ node.situation }}</p>
        </div>

        <div v-if="node.turning_point" class="detail-section">
          <h4>转折点</h4>
          <p>{{ node.turning_point }}</p>
        </div>

        <div v-if="node.emotional_arc" class="detail-section">
          <h4>情绪弧</h4>
          <p>{{ node.emotional_arc }}</p>
        </div>

        <div v-if="node.characters?.length" class="detail-section">
          <h4>角色</h4>
          <div v-for="char in node.characters" :key="char.name" class="character-item">
            <span class="char-name">{{ char.name }}</span>
            <span v-if="char.state_before" class="char-state">{{ char.state_before }}</span>
          </div>
        </div>

        <div v-if="node.relationship_delta?.length" class="detail-section">
          <h4>关系变化</h4>
          <div v-for="rel in node.relationship_delta" :key="rel.pair" class="rel-item">
            <span class="rel-pair">{{ rel.pair }}</span>
            <span>{{ rel.from_state }} → {{ rel.to_state }}</span>
          </div>
        </div>

        <div v-if="node.mood_tone" class="detail-section">
          <h4>氛围</h4>
          <p>{{ node.mood_tone }}</p>
        </div>

        <div v-if="node.narrative_rhythm" class="detail-section">
          <h4>节奏</h4>
          <p>{{ node.narrative_rhythm }}</p>
        </div>

        <div v-if="node.discussion_prompts?.length" class="detail-section">
          <h4>讨论锚点</h4>
          <ul>
            <li v-for="(prompt, i) in node.discussion_prompts" :key="i">{{ prompt }}</li>
          </ul>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import type { NarrativeNode } from '../api'

defineProps<{ node: NarrativeNode | null }>()
const emit = defineEmits<{ close: [] }>()
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-surface);
  border-radius: 12px;
  padding: 24px;
  max-width: 560px;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-right: 24px;
}

.detail-section {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.detail-row {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 14px;
}

.detail-row .label {
  color: var(--color-text-secondary);
}

.role-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: white;
}

.role-opening { background: var(--color-role-opening); }
.role-rising { background: var(--color-role-rising); }
.role-climax { background: var(--color-role-climax); }
.role-ending { background: var(--color-role-ending); }

.character-item,
.rel-item {
  font-size: 14px;
  margin-bottom: 4px;
}

.char-name {
  font-weight: 500;
  margin-right: 8px;
}

.char-state,
.rel-pair {
  color: var(--color-text-secondary);
}
</style>
```

---

### Task 11: TimelineView Component

**Files:**
- Create: `web/src/components/TimelineView.vue`

---

- [ ] **Step 1: Create web/src/components/TimelineView.vue**

```vue
<template>
  <div class="timeline-view">
    <div v-for="threadId in orderedThreadIds" :key="threadId" class="timeline-row">
      <div class="thread-header">
        <span class="thread-name">{{ threadId }}</span>
      </div>
      <div class="thread-line">
        <TimelineNode
          v-for="node in nodesByThread[threadId]"
          :key="node.id"
          :node="node"
          @click="selectedNode = node"
        />
      </div>
    </div>
    <NodeDetail :node="selectedNode" @close="selectedNode = null" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { NarrativeNode } from '../api'
import TimelineNode from './TimelineNode.vue'
import NodeDetail from './NodeDetail.vue'

const props = defineProps<{
  nodesByThread: Record<string, NarrativeNode[]>
}>()

const selectedNode = ref<NarrativeNode | null>(null)

const orderedThreadIds = computed(() => {
  return Object.keys(props.nodesByThread).sort()
})
</script>

<style scoped>
.timeline-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.timeline-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thread-header {
  position: sticky;
  left: 0;
}

.thread-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 4px 8px;
  border-radius: 4px;
}

.thread-line {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 8px 0;
}
</style>
```

---

## Chunk 6: BookDetailView

### Task 12: BookDetailView Component

**Files:**
- Create: `web/src/views/BookDetailView.vue`

---

- [ ] **Step 1: Create web/src/views/BookDetailView.vue**

```vue
<template>
  <div class="book-detail-view">
    <div v-if="store.loading" class="loading">加载中...</div>
    <div v-else-if="store.error" class="error">{{ store.error }}</div>
    <template v-else>
      <div class="book-header">
        <button class="back-btn" @click="goBack">← 返回</button>
        <h2 class="book-title">{{ store.currentBook?.title }}</h2>
        <span class="node-count">{{ store.nodes.length }} 节点</span>
      </div>

      <FilterBar
        :threads="store.threadIds"
        :initial-filter="filter"
        @filter="handleFilter"
      />

      <TimelineView :nodes-by-thread="filteredNodesByThread" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBooksStore } from '../stores/books'
import type { NarrativeNode } from '../api'
import FilterBar from '../components/FilterBar.vue'
import TimelineView from '../components/TimelineView.vue'

interface NodeFilter {
  search: string
  narrativeRoles: string[]
  visibleThreads: string[]
}

const route = useRoute()
const router = useRouter()
const store = useBooksStore()

const filter = ref<NodeFilter>({
  search: '',
  narrativeRoles: [],
  visibleThreads: [],
})

const filteredNodesByThread = computed(() => {
  const result: Record<string, NarrativeNode[]> = {}

  for (const [threadId, nodes] of Object.entries(store.nodesByThread)) {
    if (filter.value.visibleThreads.length > 0 && !filter.value.visibleThreads.includes(threadId)) {
      continue
    }

    const filtered = nodes.filter((node) => {
      // Role filter
      if (filter.value.narrativeRoles.length > 0 && !filter.value.narrativeRoles.includes(node.narrative_role)) {
        return false
      }

      // Search filter
      if (filter.value.search) {
        const searchLower = filter.value.search.toLowerCase()
        const matchScene = node.scene?.toLowerCase().includes(searchLower)
        const matchSituation = node.situation?.toLowerCase().includes(searchLower)
        if (!matchScene && !matchSituation) return false
      }

      return true
    })

    if (filtered.length > 0) {
      result[threadId] = filtered
    }
  }

  return result
})

function handleFilter(newFilter: NodeFilter) {
  filter.value = newFilter
}

function goBack() {
  store.clearCurrentBook()
  router.push('/')
}

onMounted(() => {
  const bookId = route.params.id as string
  store.fetchBookNodes(bookId)
})
</script>

<style scoped>
.book-detail-view {
  max-width: 1000px;
  margin: 0 auto;
}

.loading,
.error {
  text-align: center;
  padding: 48px;
}

.book-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.back-btn {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover {
  background: var(--color-bg);
}

.book-title {
  font-size: 24px;
  font-weight: 600;
  flex: 1;
}

.node-count {
  font-size: 14px;
  color: var(--color-text-secondary);
}
</style>
```

---

## Summary

**Files Created:**

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
│   │   ├── BookList.vue
│   │   ├── FilterBar.vue
│   │   ├── TimelineView.vue
│   │   ├── TimelineNode.vue
│   │   └── NodeDetail.vue
│   └── styles/
│       └── variables.css
```

**Implementation Order:**
1. Chunk 1: Project scaffolding (package.json, vite config, entry files)
2. Chunk 2: API layer
3. Chunk 3: Pinia store
4. Chunk 4: Core components (Header, BookCard, BookList, UploadArea)
5. Chunk 5: Detail components (FilterBar, TimelineNode, NodeDetail, TimelineView)
6. Chunk 6: Views (HomeView, BookDetailView)

**Run Commands:**
```bash
cd web
npm install
npm run dev
```
