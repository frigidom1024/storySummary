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
