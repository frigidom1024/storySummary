<template>
  <header class="header">
    <div class="header-content">
      <router-link to="/" class="logo">Story Summary</router-link>

      <div class="header-actions" v-if="authStore.isAuthenticated">
        <div class="user-info">
          <span class="user-avatar">{{ userInitial }}</span>
          <span class="user-name">{{ authStore.user?.username }}</span>
        </div>
        <button class="logout-btn" @click="handleLogout">登出</button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const userInitial = computed(() => {
  return authStore.user?.username?.charAt(0).toUpperCase() || 'U'
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
}

.logo:hover {
  text-decoration: none;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.user-name {
  font-size: var(--font-size-sm);
  color: var(--color-text);
  font-weight: 500;
}

.logout-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-text-tertiary);
  color: var(--color-text);
}
</style>
