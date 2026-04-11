<template>
  <div class="book-detail-view">
    <div v-if="store.loading" class="loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="store.error" class="error-state">
      {{ store.error }}
    </div>

    <template v-else>
      <div class="book-header">
        <button class="back-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          返回
        </button>
        <h2 class="book-title">{{ title }}</h2>
        <span class="node-count">{{ store.nodes.length }} 节点</span>
      </div>

      <FilterBar
        v-if="store.threadIds.length > 0"
        :threads="store.threadIds"
        :initial-filter="filter"
        @filter="handleFilter"
      />

      <TimelineView v-if="Object.keys(filteredNodesByThread).length > 0" :nodes-by-thread="filteredNodesByThread" />

      <div v-else class="empty-nodes">
        暂无节点数据
      </div>
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

const title = computed(() => {
  return (store.currentBook as any)?.title || '书籍详情'
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

.empty-nodes {
  text-align: center;
  padding: 48px;
  color: var(--color-text-secondary);
}
</style>
