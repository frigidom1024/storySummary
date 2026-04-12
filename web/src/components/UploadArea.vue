<template>
  <div class="upload-section">
    <!-- 初始状态：上传区域 -->
    <div
      v-if="!showForm && !uploading && !uploadResult"
      class="upload-area"
      :class="{ dragging: isDragging }"
      @click="triggerFileInput"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".epub,.txt"
        style="display: none"
        @change="handleFileSelect"
      />
      <div class="upload-content">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <span class="upload-text">拖拽 epub 或 txt 文件到此处，或点击选择</span>
        <span class="upload-hint">支持 .epub 和 .txt 格式</span>
      </div>
    </div>

    <!-- 上传中状态 -->
    <div v-else-if="uploading" class="upload-status">
      <div class="spinner"></div>
      <span>{{ statusMessage }}</span>
    </div>

    <!-- 上传结果状态 -->
    <div v-else-if="uploadResult" class="upload-result">
      <div v-if="uploadResult.success" class="result-success">
        <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 6L9 17l-5-5"/>
        </svg>
        <span>上传成功！</span>
        <button class="reset-btn" @click="reset">继续上传</button>
      </div>
      <div v-else class="result-error">
        <span>{{ uploadResult.error }}</span>
        <button class="reset-btn" @click="reset">重试</button>
      </div>
    </div>

    <!-- epub/txt 输入表单 -->
    <div v-else class="create-form">
      <div class="form-header">
        <h3>填写书籍信息</h3>
        <button class="close-btn" @click="reset">取消</button>
      </div>
      <form @submit.prevent="confirmUpload">
        <div class="form-group">
          <input
            v-model="formData.title"
            type="text"
            placeholder="输入书名（必填）"
            required
            autofocus
          />
        </div>
        <div class="form-group">
          <input
            v-model="formData.author"
            type="text"
            placeholder="作者（选填）"
          />
        </div>
        <div class="form-group">
          <input
            v-model="formData.publisher"
            type="text"
            placeholder="出版社（选填）"
          />
        </div>
        <button type="submit" class="submit-btn" :disabled="!formData.title.trim()">
          上传
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useBooksStore } from '../stores/books'

const store = useBooksStore()

const fileInput = ref<HTMLInputElement | null>(null)
const showForm = ref(false)
const isDragging = ref(false)
const uploading = ref(false)
const statusMessage = ref('')
const selectedFile = ref<File | null>(null)
const uploadResult = ref<{ success: boolean; error?: string } | null>(null)

const formData = reactive({
  title: '',
  author: '',
  publisher: '',
})

function triggerFileInput() {
  fileInput.value?.click()
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) processFile(file)
}

function handleFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) processFile(file)
}

function processFile(file: File) {
  const ext = file.name.toLowerCase().split('.').pop()
  if (ext !== 'epub' && ext !== 'txt') {
    uploadResult.value = { success: false, error: '不支持的文件类型' }
    return
  }
  selectedFile.value = file
  // 用文件名作为默认书名
  if (ext === 'epub') {
    formData.title = file.name.replace(/\.epub$/i, '')
  } else {
    formData.title = file.name.replace(/\.txt$/i, '')
  }
  showForm.value = true
}

async function confirmUpload() {
  if (!selectedFile.value || !formData.title.trim()) return

  uploading.value = true
  statusMessage.value = '正在上传...'
  showForm.value = false

  const result = await store.uploadBook(selectedFile.value, {
    title: formData.title.trim(),
    author: formData.author.trim() || undefined,
    publisher: formData.publisher.trim() || undefined,
  })

  uploading.value = false

  if (result) {
    uploadResult.value = { success: true }
  } else {
    uploadResult.value = { success: false, error: store.error || '上传失败' }
  }
}

function reset() {
  showForm.value = false
  isDragging.value = false
  uploading.value = false
  uploadResult.value = null
  selectedFile.value = null
  formData.title = ''
  formData.author = ''
  formData.publisher = ''
  if (fileInput.value) fileInput.value.value = ''
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
  gap: 8px;
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: var(--color-text-tertiary);
}

.upload-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.upload-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.upload-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
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

.upload-result {
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.result-success {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #15803d;
}

.check-icon {
  width: 20px;
  height: 20px;
}

.result-error {
  color: #b91c1c;
}

.reset-btn {
  margin-left: auto;
  padding: 4px 12px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
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
  margin-bottom: 12px;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
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
