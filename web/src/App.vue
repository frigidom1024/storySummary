<template>
  <div class="app">
    <Header />
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import Header from './components/Header.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  authStore.initAuth()
})
</script>

<style>
.app {
  min-height: 100vh;
  background: var(--color-bg);
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
}
</style>
