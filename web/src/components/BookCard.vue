<template>
  <div class="book-card" @click="onClick">
    <div class="card-header">
      <h3 class="book-title">{{ book.title }}</h3>
      <span class="status-badge" :class="statusClass">{{ statusText }}</span>
    </div>
    <div class="book-meta">
      <span class="created-at">{{ formatDate(book.created_at) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Book } from '../api'

const props = defineProps<{ book: Book }>()
const router = useRouter()

const statusClass = computed(() => {
  switch (props.book.status) {
    case 'completed': return 'status-completed'
    case 'processing': return 'status-processing'
    case 'failed': return 'status-failed'
    default: return 'status-pending'
  }
})

const statusText = computed(() => {
  switch (props.book.status) {
    case 'completed': return '已完成'
    case 'processing': return '处理中'
    case 'failed': return '失败'
    default: return '等待中'
  }
})

function onClick() {
  if (props.book.status === 'completed') {
    router.push(`/books/${props.book.id}`)
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<style scoped>
.book-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.book-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.book-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.4;
}

.status-badge {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 500;
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

.book-meta {
  display: flex;
  gap: 12px;
}

.created-at {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
</style>
