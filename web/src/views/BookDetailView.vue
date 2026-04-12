<template>
  <div class="book-detail-view">
    <!-- 加载状态 -->
    <div v-if="pageState.isLoading.value && !book" class="loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="pageState.error.value" class="error-state">
      {{ pageState.error.value }}
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

      <!-- 口播稿生成区域 -->
      <div v-if="book.status === 'completed'" class="manuscript-section">
        <div class="section-header" @click="toggleManuscriptPanel">
          <h3>生成口播稿</h3>
          <button class="toggle-btn">{{ showManuscriptPanel ? '收起' : '展开' }}</button>
        </div>

        <div v-if="showManuscriptPanel" class="manuscript-panel">
          <div class="option-group">
            <label class="option-label">风格选择</label>
            <select v-model="manuscriptOptions.style_key" class="style-select">
              <option v-for="opt in STYLE_OPTIONS" :key="opt.key" :value="opt.key">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div class="option-group">
            <label class="option-label">自定义规则（可选）</label>
            <textarea
              v-model="manuscriptOptions.custom_rules"
              class="custom-rules-input"
              placeholder="例如：增加更多个人感悟..."
              rows="3"
            ></textarea>
          </div>

          <div class="option-group">
            <label class="option-label">参考口播稿（可选）</label>
            <textarea
              v-model="manuscriptOptions.reference_script"
              class="reference-input"
              placeholder="粘贴一段参考的口播稿，AI会学习此风格..."
              rows="5"
            ></textarea>
          </div>

          <button
            class="generate-btn"
            @click="generateManuscript"
            :disabled="isGeneratingManuscript"
          >
            {{ isGeneratingManuscript ? '生成中...' : '开始生成' }}
          </button>

          <!-- 生成进度 -->
          <div v-if="isGeneratingManuscript" class="manuscript-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (manuscriptProgress?.progress || 0) + '%' }"></div>
            </div>
            <div class="progress-text">{{ manuscriptProgress?.message || '正在启动生成...' }}</div>
          </div>

          <div v-if="manuscriptError" class="error-message">{{ manuscriptError }}</div>

          <!-- 生成结果 -->
          <div v-if="manuscriptResult" class="manuscript-result">
            <div class="result-header">
              <span>口播稿已生成</span>
            </div>
            <div class="manuscript-content">{{ manuscriptResult.manuscript }}</div>
          </div>
        </div>
      </div>

      <!-- AI 解析按钮 -->
      <div v-if="book.status === 'pending' || book.status === 'failed'" class="analyze-section">
        <button class="analyze-btn" @click="startAnalyze" :disabled="pageState.isAnalyzing.value">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
          {{ pageState.isAnalyzing.value ? '解析中...' : '开始 AI 解析' }}
        </button>
      </div>

      <!-- 错误提示（实时分析错误） -->
      <div v-if="pageState.error.value" class="error-message">
        {{ pageState.error.value }}
      </div>

      <!-- 错误提示（已保存的错误消息） -->
      <div v-if="book.status === 'failed' && book.message && !pageState.error.value" class="error-message">
        {{ book.message }}
      </div>

      <!-- 解析进度 -->
      <div v-if="pageState.isAnalyzing.value" class="progress-section">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: pageState.progress.value + '%' }"></div>
        </div>
        <div class="progress-text">{{ pageState.progressMessage.value }}</div>
      </div>

      <!-- 筛选器 -->
      <FilterBar
        v-if="store.threadIds.length > 0"
        :threads="store.threadIds"
        :initial-filter="filter"
        @filter="handleFilter"
      />

      <!-- 视图切换 -->
      <div v-if="store.nodes.length > 0" class="view-toggle">
        <button :class="{ active: pageState.viewMode.value === 'graph' }" @click="pageState.setViewMode('graph')">
          图谱
        </button>
        <button :class="{ active: pageState.viewMode.value === 'timeline' }" @click="pageState.setViewMode('timeline')">
          时间线
        </button>
      </div>

      <!-- 图谱视图 -->
      <NodeGraph v-if="pageState.viewMode.value === 'graph' && store.nodes.length > 0" :nodes="store.nodes" />

      <!-- 时间线视图 -->
      <TimelineView v-else-if="pageState.viewMode.value === 'timeline' && Object.keys(filteredNodesByThread).length > 0" :nodes-by-thread="filteredNodesByThread" />

      <div v-else-if="store.nodes.length === 0 && !pageState.isAnalyzing.value" class="empty-nodes">
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
import type { NarrativeNode, ManuscriptResponse } from '../api'
import { createPageStateMachine } from '../composables/usePageStateMachine'
import FilterBar from '../components/FilterBar.vue'
import TimelineView from '../components/TimelineView.vue'
import NodeGraph from '../components/NodeGraph.vue'

// 预设风格
const STYLE_OPTIONS = [
  { key: '', label: '默认风格' },
  { key: '轻松聊天', label: '轻松聊天' },
  { key: '深度解读', label: '深度解读' },
  { key: '故事讲述', label: '故事讲述' },
  { key: '专业评论', label: '专业评论' },
]

interface NodeFilter {
  search: string
  narrativeRoles: string[]
  visibleThreads: string[]
}

// 口播稿生成相关状态
const showManuscriptPanel = ref(false)
const manuscriptOptions = ref({
  style_key: '',
  custom_rules: '',
  reference_script: '',
})
const isGeneratingManuscript = ref(false)
const manuscriptResult = ref<ManuscriptResponse | null>(null)
const manuscriptError = ref<string | null>(null)
const manuscriptProgress = ref<{ progress: number; message: string; status: string } | null>(null)
let manuscriptFetchRetries = 0
const MAX_MANUSCRIPT_RETRIES = 3

const route = useRoute()
const router = useRouter()
const store = useBooksStore()

const pageState = createPageStateMachine()

const filter = ref<NodeFilter>({
  search: '',
  narrativeRoles: [],
  visibleThreads: [],
})

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

  pageState.clearError()
  pageState.startAnalyze('准备启动...')
  wsProgress.value = { progress: 0, message: '准备启动...', status: 'processing' }

  connectWebSocket()

  try {
    await booksApi.analyzeBook(book.value.id)
  } catch (e: any) {
    pageState.fail(e.response?.data?.message || e.message || '启动分析失败')
    disconnectWebSocket()
  }
}

function connectWebSocket() {
  if (!book.value) return

  // 如果已有连接，先断开
  if (ws) {
    ws.close()
    ws = null
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//localhost:8000/api/books/${book.value.id}/ws`

  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    if (event.data === 'pong') return
    try {
      const data = JSON.parse(event.data)

      // 处理口播稿生成进度
      if (isGeneratingManuscript.value) {
        manuscriptProgress.value = data

        if (data.status === 'completed') {
          // 获取生成的口播稿，带重试
          fetchManuscriptWithRetry(book.value!.id)
        } else if (data.status === 'failed') {
          isGeneratingManuscript.value = false
          manuscriptError.value = data.message || '生成失败'
        }
        return
      }

      // 处理书籍分析进度
      wsProgress.value = data
      pageState.updateProgress(data.progress, data.message)

      if (data.status === 'completed') {
        pageState.complete()
        store.fetchBookNodes(book.value!.id)
      } else if (data.status === 'failed') {
        pageState.fail(data.message || '解析失败')
      }
    } catch (e) {
      console.error('WebSocket message parse error:', e)
    }
  }

  ws.onclose = (event) => {
    console.log('WebSocket closed', event.code, event.reason)
    ws = null

    // 如果是口播稿生成中，尝试重连
    if (isGeneratingManuscript.value && manuscriptFetchRetries < MAX_MANUSCRIPT_RETRIES) {
      console.log('WebSocket 断开，尝试重连...')
      setTimeout(() => {
        if (isGeneratingManuscript.value) {
          connectWebSocket()
        }
      }, 1000)
      return
    }

    if (pageState.isAnalyzing.value && !wsProgress.value?.status) {
      pageState.fail('WebSocket 连接断开，请重试')
    }
  }

  ws.onerror = (e) => {
    console.error('WebSocket error:', e)
    if (isGeneratingManuscript.value) {
      manuscriptError.value = 'WebSocket 连接错误'
    }
    if (pageState.isAnalyzing.value) {
      pageState.fail('WebSocket 连接错误，请重试')
    }
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}

async function generateManuscript() {
  if (!book.value) return

  isGeneratingManuscript.value = true
  manuscriptError.value = null
  manuscriptResult.value = null
  manuscriptProgress.value = null
  manuscriptFetchRetries = 0

  // 确保 WebSocket 已连接
  if (!ws) {
    connectWebSocket()
  }

  try {
    const options = {
      style_key: manuscriptOptions.value.style_key || undefined,
      custom_rules: manuscriptOptions.value.custom_rules || undefined,
      reference_script: manuscriptOptions.value.reference_script || undefined,
    }
    await booksApi.generateManuscript(book.value.id, options)
    // 进度将通过 WebSocket 更新
  } catch (e: any) {
    manuscriptError.value = e.response?.data?.detail || e.message || '启动生成失败'
    isGeneratingManuscript.value = false
  }
}

async function fetchManuscriptWithRetry(bookId: string) {
  try {
    const res = await booksApi.getManuscript(bookId)
    manuscriptResult.value = res.data
    showManuscriptPanel.value = true
    manuscriptFetchRetries = 0
  } catch (e: any) {
    manuscriptFetchRetries++
    const errorMsg = e.response?.data?.detail || e.message || '未知错误'

    if (manuscriptFetchRetries < MAX_MANUSCRIPT_RETRIES) {
      // 重试
      console.log(`获取口播稿失败，${1000 * manuscriptFetchRetries}ms 后重试...`)
      setTimeout(() => {
        fetchManuscriptWithRetry(bookId)
      }, 1000 * manuscriptFetchRetries)
    } else {
      manuscriptError.value = `获取口播稿失败: ${errorMsg}，请稍后刷新页面重试`
      manuscriptFetchRetries = 0
    }
  } finally {
    isGeneratingManuscript.value = false
  }
}

function toggleManuscriptPanel() {
  showManuscriptPanel.value = !showManuscriptPanel.value
}

onMounted(async () => {
  const bookId = route.params.id as string
  pageState.setLoading()

  try {
    const res = await booksApi.getBook(bookId)
    store.currentBook = res.data
  } catch (e: any) {
    pageState.fail(e.response?.data?.detail || '获取书籍详情失败')
    return
  }

  if (store.currentBook?.status === 'completed') {
    await store.fetchBookNodes(bookId)
    const res = await booksApi.getBook(bookId)
    store.currentBook = res.data
    pageState.complete()
  }

  if (store.currentBook?.status === 'processing') {
    pageState.startAnalyze('继续解析...')
    connectWebSocket()
  } else {
    pageState.state.value = 'idle'
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

.error-message {
  padding: 12px 16px;
  background: rgba(234, 67, 53, 0.1);
  border: 1px solid rgba(234, 67, 53, 0.3);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin-bottom: 16px;
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

/* 视图切换 */
.view-toggle {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  width: fit-content;
}

.view-toggle button {
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.view-toggle button:hover {
  color: var(--color-text);
}

.view-toggle button.active {
  background: var(--color-primary);
  color: white;
}

/* 口播稿生成区域 */
.manuscript-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
}

.section-header:hover {
  background: var(--color-surface-hover);
}

.section-header h3 {
  font-size: var(--font-size-base);
  font-weight: 600;
  margin: 0;
}

.toggle-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 4px 12px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.manuscript-panel {
  padding: 0 20px 20px;
  border-top: 1px solid var(--color-border);
}

.option-group {
  margin-top: 16px;
}

.option-label {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.style-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-bg);
  color: var(--color-text);
}

.custom-rules-input,
.reference-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-bg);
  color: var(--color-text);
  resize: vertical;
  font-family: inherit;
}

.generate-btn {
  width: 100%;
  padding: 12px;
  margin-top: 16px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.generate-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.manuscript-progress {
  margin-top: 16px;
}

.manuscript-progress .progress-bar {
  height: 6px;
  background: var(--color-border-light);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.manuscript-progress .progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.manuscript-progress .progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: 8px;
  text-align: center;
}

.manuscript-result {
  margin-top: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.result-header {
  padding: 10px 14px;
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.manuscript-content {
  padding: 16px;
  font-size: var(--font-size-sm);
  line-height: 1.7;
  white-space: pre-wrap;
  max-height: 500px;
  overflow-y: auto;
}
</style>