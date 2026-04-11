<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1 class="logo">Story Summary</h1>
        <p class="subtitle">登录到您的账户</p>
      </div>

      <form @submit.prevent="handleSubmit" class="login-form">
        <div v-if="isRegister" class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
            autocomplete="email"
          />
        </div>

        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="username"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="••••••••"
            required
            autocomplete="current-password"
          />
        </div>

        <div v-if="authStore.error" class="error-message">
          {{ authStore.error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="authStore.loading">
          <span v-if="authStore.loading" class="spinner"></span>
          <span v-else>{{ isRegister ? '注册' : '登录' }}</span>
        </button>
      </form>

      <div class="login-footer">
        <button class="toggle-btn" @click="toggleMode">
          {{ isRegister ? '已有账户？登录' : '没有账户？注册' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isRegister = ref(false)
const username = ref('')
const email = ref('')
const password = ref('')

function toggleMode() {
  isRegister.value = !isRegister.value
  authStore.error = null
}

async function handleSubmit() {
  authStore.error = null

  let success: boolean
  if (isRegister.value) {
    success = await authStore.register(username.value, email.value, password.value)
  } else {
    success = await authStore.login(username.value, password.value)
  }

  if (success) {
    router.push('/')
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 48px 40px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 8px;
}

.subtitle {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
}

.form-group input {
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  background: var(--color-bg);
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.form-group input::placeholder {
  color: var(--color-text-tertiary);
}

.error-message {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  text-align: center;
  padding: 12px;
  background: rgba(234, 67, 53, 0.08);
  border-radius: var(--radius-md);
}

.submit-btn {
  width: 100%;
  padding: 12px 24px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast), box-shadow var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-md);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  margin-top: 24px;
  text-align: center;
}

.toggle-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.toggle-btn:hover {
  background: var(--color-primary-light);
}
</style>
