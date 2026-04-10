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
