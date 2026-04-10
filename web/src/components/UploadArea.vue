<template>
  <div
    class="upload-area"
    :class="{ dragging: isDragging, uploading: uploading }"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".txt,.epub"
      @change="handleFileChange"
      style="display: none"
    />
    <div v-if="uploading" class="upload-progress">
      <div class="spinner"></div>
      <span>{{ statusMessage }}</span>
    </div>
    <div v-else class="upload-hint">
      <span class="upload-icon">+</span>
      <span>拖拽文件或点击上传 ( TXT / EPUB )</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useBooksStore } from '../stores/books'

const store = useBooksStore()
const fileInput = ref<HTMLInputElement>()
const isDragging = ref(false)
const uploading = ref(false)
const statusMessage = ref('')

function triggerFileInput() {
  fileInput.value?.click()
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) uploadFile(file)
}

function handleFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) uploadFile(file)
}

async function uploadFile(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['txt', 'epub'].includes(ext || '')) {
    alert('仅支持 TXT 和 EPUB 文件')
    return
  }

  uploading.value = true
  statusMessage.value = '上传中...'

  try {
    await store.uploadBook(file)
    statusMessage.value = '上传成功，处理中...'
    await store.fetchBooks()
    statusMessage.value = '完成'
  } catch (e) {
    statusMessage.value = '上传失败'
    alert('上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-area {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover,
.upload-area.dragging {
  border-color: var(--color-primary);
  background: rgba(59, 130, 246, 0.05);
}

.upload-area.uploading {
  cursor: default;
}

.upload-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
}

.upload-icon {
  font-size: 32px;
  color: var(--color-primary);
}

.upload-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
