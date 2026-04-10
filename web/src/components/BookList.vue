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
