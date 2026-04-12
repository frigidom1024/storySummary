<template>
  <div class="book-card" @click="onClick">
    <div class="card-content">
      <div v-if="book.cover_url" class="card-cover">
        <img :src="book.cover_url" :alt="book.title" />
      </div>
      <div v-else class="card-cover placeholder">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
      </div>
      <div class="card-info">
        <div class="card-header">
          <h3 class="book-title">{{ book.title }}</h3>
          <span class="status-badge" :class="statusClass">{{ statusText }}</span>
        </div>
        <div v-if="book.author || book.publisher" class="book-meta">
          <span v-if="book.author" class="author">{{ book.author }}</span>
          <span v-if="book.author && book.publisher" class="separator">·</span>
          <span v-if="book.publisher" class="publisher">{{ book.publisher }}</span>
        </div>
        <div class="book-date">
          <span>{{ formatDate(book.created_at) }}</span>
        </div>
      </div>
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
  router.push(`/books/${props.book.id}`)
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
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.book-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary);
}

.card-content {
  display: flex;
  gap: 16px;
}

.card-cover {
  flex-shrink: 0;
  width: 80px;
  height: 110px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-cover.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-border-light);
  color: var(--color-text-tertiary);
}

.card-cover.placeholder svg {
  width: 32px;
  height: 32px;
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.book-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.status-badge {
  flex-shrink: 0;
  padding: 3px 8px;
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
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  display: flex;
  gap: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.separator {
  color: var(--color-text-tertiary);
}

.book-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: auto;
}
</style>
