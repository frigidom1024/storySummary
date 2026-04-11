<template>
  <div class="home-view">
    <div class="page-header">
      <h1 class="page-title">我的书籍</h1>
    </div>

    <UploadArea />

    <div v-if="store.loading" class="loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="store.error" class="error-state">
      {{ store.error }}
    </div>

    <div v-else-if="store.books.length === 0" class="empty-state">
      <p>还没有书籍，创建一本开始吧</p>
    </div>

    <BookList v-else :books="store.books" />
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

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text);
}

.loading,
.error-state,
.empty-state {
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
</style>
