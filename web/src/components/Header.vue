<template>
  <header class="header">
    <div class="header-content">
      <h1 class="logo" @click="router.push('/')">Story Summary</h1>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 16px 24px;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
}

.logo {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  cursor: pointer;
}

.logo:hover {
  color: var(--color-primary);
}
</style>
