<template>
  <div class="book-detail-view">
    <!-- 加载状态 -->
    <div v-if="store.loading && !book" class="loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="store.error" class="error-state">
      {{ store.error }}
    </div>

    <!-- 书籍基本信息 -->
    <template v-else-if="book">
      <div class="book-header">
        <button class="back-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          返回
        </button>
        <h2 class="book-title">{{ book.title }}</h2>
        <span class="node-count">{{ store.nodes.length }} 节点</span>
      </div>

      <!-- 书籍信息卡片 -->
      <div class="book-info-card">
        <div class="book-cover" v-if="book.cover_url">
          <img :src="book.cover_url" :alt="book.title" />
        </div>
        <div class="book-meta">
          <div class="meta-item" v-if="book.author">
            <span class="meta-label">作者</span>
            <span class="meta-value">{{ book.author }}</span>
          </div>
          <div class="meta-item" v-if="book.publisher">
            <span class="meta-label">出版社</span>
            <span class="meta-value">{{ book.publisher }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">状态</span>
            <span class="meta-value status-badge" :class="statusClass">{{ statusText }}</span>
          </div>
        </div>
      </div>

      <!-- AI 解析按钮 -->
      <div v-if="book.status === 'pending' || book.status === 'failed'" class="analyze-section">
        <button class="analyze-btn" @click="startAnalyze" :disabled="analyzing">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
          {{ analyzing ? '解析中...' : '开始 AI 解析' }}
        </button>
      </div>

      <!-- 解析进度 -->
      <div v-if="analyzing || wsProgress" class="progress-section">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: (wsProgress?.progress || 0) + '%' }"></div>
        </div>
        <div class="progress-text">{{ wsProgress?.message || '准备中...' }}</div>
      </div>

      <!-- 筛选器 -->
      <FilterBar
        v-if="store.threadIds.length > 0"
        :threads="store.threadIds"
        :initial-filter="filter"
        @filter="handleFilter"
      />

      <!-- 时间线视图 -->
      <TimelineView v-if="Object.keys(filteredNodesByThread).length > 0" :nodes-by-thread="filteredNodesByThread" />

      <div v-else-if="store.nodes.length === 0 && !analyzing && !wsProgress" class="empty-nodes">
        点击上方按钮开始 AI 解析
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBooksStore } from '../stores/books'
import { booksApi } from '../api'
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

const analyzing = ref(false)
const wsProgress = ref<{ progress: number; message: string; status: string } | null>(null)
let ws: WebSocket | null = null

const book = computed(() => store.currentBook)

const statusClass = computed(() => {
  switch (book.value?.status) {
    case 'completed': return 'status-completed'
    case 'processing': return 'status-processing'
    case 'failed': return 'status-failed'
    default: return 'status-pending'
  }
})

const statusText = computed(() => {
  switch (book.value?.status) {
    case 'completed': return '已完成'
    case 'processing': return '处理中'
    case 'failed': return '失败'
    default: return '等待中'
  }
})

const filteredNodesByThread = computed(() => {
  const result: Record<string, NarrativeNode[]> = {}

  for (const [threadId, nodes] of Object.entries(store.nodesByThread)) {
    if (filter.value.visibleThreads.length > 0 && !filter.value.visibleThreads.includes(threadId)) {
      continue
    }

    const filtered = nodes.filter((node) => {
      if (filter.value.narrativeRoles.length > 0 && !filter.value.narrativeRoles.includes(node.narrative_role)) {
        return false
      }

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

async function startAnalyze() {
  if (!book.value) return

  analyzing.value = true
  wsProgress.value = { progress: 0, message: '准备启动...', status: 'processing' }

  // 启动分析
  try {
    await booksApi.analyzeBook(book.value.id)
  } catch (e) {
    console.error('Failed to start analysis:', e)
  }

  // 连接 WebSocket
  connectWebSocket()
}

function connectWebSocket() {
  if (!book.value) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//localhost:8000/api/books/${book.value.id}/ws`

  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    if (event.data === 'pong') return
    try {
      const data = JSON.parse(event.data)
      wsProgress.value = data

      if (data.status === 'completed' || data.status === 'failed') {
        analyzing.value = false
        if (data.status === 'completed') {
          // 刷新节点
          store.fetchBookNodes(book.value!.id)
        }
      }
    } catch (e) {
      console.error('WebSocket message parse error:', e)
    }
  }

  ws.onclose = () => {
    ws = null
  }

  ws.onerror = (e) => {
    console.error('WebSocket error:', e)
    analyzing.value = false
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}

onMounted(async () => {
  const bookId = route.params.id as string

  // 先获取书籍信息
  try {
    const res = await booksApi.getBook(bookId)
    store.currentBook = res.data
  } catch (e: any) {
    store.error = e.response?.data?.detail || '获取书籍详情失败'
    return
  }

  // 如果有节点数据，获取节点
  if (store.currentBook?.status === 'completed') {
    await store.fetchBookNodes(bookId)
    // 重新设置完整的 book 信息
    const res = await booksApi.getBook(bookId)
    store.currentBook = res.data
  }

  // 如果正在处理中，连接 WebSocket
  if (store.currentBook?.status === 'processing') {
    analyzing.value = true
    connectWebSocket()
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.book-detail-view {
  max-width: 1000px;
  margin: 0 auto;
}

.loading,
.error-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--color-text-secondary);
}

.error-state {
  color: var(--color-error);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.book-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.back-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.back-btn svg {
  width: 16px;
  height: 16px;
}

.book-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  flex: 1;
}

.node-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* 书籍信息卡片 */
.book-info-card {
  display: flex;
  gap: 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
}

.book-cover {
  flex-shrink: 0;
  width: 120px;
  height: 160px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.book-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.book-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-item {
  display: flex;
  gap: 12px;
}

.meta-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  min-width: 60px;
}

.meta-value {
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.status-badge {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
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

/* AI 解析按钮 */
.analyze-section {
  margin-bottom: 24px;
}

.analyze-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 16px 24px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.analyze-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.analyze-btn svg {
  width: 20px;
  height: 20px;
}

/* 解析进度 */
.progress-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 24px;
}

.progress-bar {
  height: 8px;
  background: var(--color-border-light);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
}

/* 空状态 */
.empty-nodes {
  text-align: center;
  padding: 48px;
  color: var(--color-text-secondary);
}
</style>
