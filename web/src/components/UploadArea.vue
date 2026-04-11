<template>
  <div class="upload-section">
    <div v-if="!showForm" class="upload-area" :class="{ dragging: isDragging }" @click="showForm = true">
      <div class="upload-content">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <span class="upload-text">上传书籍</span>
      </div>
    </div>

    <div v-else class="create-form">
      <div class="form-header">
        <h3>创建新书籍</h3>
        <button class="close-btn" @click="closeForm">取消</button>
      </div>
      <form @submit.prevent="handleCreate">
        <div class="form-group">
          <input
            v-model="title"
            type="text"
            placeholder="输入书名"
            required
            autofocus
          />
        </div>
        <button type="submit" class="submit-btn" :disabled="!title.trim()">
          创建
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useBooksStore } from '../stores/books'

const store = useBooksStore()
const showForm = ref(false)
const isDragging = ref(false)
const title = ref('')

function closeForm() {
  showForm.value = false
  title.value = ''
}

async function handleCreate() {
  if (!title.value.trim()) return

  const book = await store.createBook(title.value.trim())
  if (book) {
    closeForm()
  }
}
</script>

<style scoped>
.upload-section {
  margin-bottom: 24px;
}

.upload-area {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
}

.upload-area:hover,
.upload-area.dragging {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: var(--color-text-tertiary);
}

.upload-area:hover .upload-icon,
.upload-area.dragging .upload-icon {
  color: var(--color-primary);
}

.upload-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.create-form {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.form-header h3 {
  font-size: var(--font-size-base);
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.close-btn:hover {
  background: var(--color-surface-hover);
}

.form-group {
  margin-bottom: 16px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
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
  transition: background var(--transition-fast);
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
