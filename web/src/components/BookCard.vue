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
