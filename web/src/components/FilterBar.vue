<template>
  <div class="filter-bar">
    <input
      v-model="localFilter.search"
      type="text"
      placeholder="搜索场景、情境..."
      class="search-input"
      @input="emitFilter"
    />
    <div class="role-filter">
      <label v-for="role in narrativeRoles" :key="role" class="role-chip">
        <input
          type="checkbox"
          :value="role"
          v-model="localFilter.narrativeRoles"
          @change="emitFilter"
        />
        <span :class="['role-label', `role-${role}`]">{{ role }}</span>
      </label>
    </div>
    <div class="thread-filter">
      <span class="filter-label">叙事线:</span>
      <label v-for="thread in threads" :key="thread" class="thread-chip">
        <input
          type="checkbox"
          :value="thread"
          v-model="localFilter.visibleThreads"
          @change="emitFilter"
        />
        <span>{{ thread }}</span>
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface NodeFilter {
  search: string
  narrativeRoles: string[]
  visibleThreads: string[]
}

const props = defineProps<{
  threads: string[]
  initialFilter?: NodeFilter
}>()

const emit = defineEmits<{
  filter: [filter: NodeFilter]
}>()

const narrativeRoles = ['opening', 'rising', 'climax', 'ending']

const localFilter = ref<NodeFilter>({
  search: '',
  narrativeRoles: [],
  visibleThreads: props.threads.length > 0 ? [...props.threads] : [],
  ...props.initialFilter,
})

watch(() => props.threads, (newThreads) => {
  if (newThreads.length > 0) {
    localFilter.value.visibleThreads = [...newThreads]
  }
})

function emitFilter() {
  emit('filter', { ...localFilter.value })
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  padding: 16px;
  background: var(--color-surface);
  border-radius: var(--radius);
  margin-bottom: 24px;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.role-filter,
.thread-filter {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.role-chip,
.thread-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.role-chip input,
.thread-chip input {
  display: none;
}

.role-label {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.role-chip input:checked + .role-label {
  opacity: 1;
}

.role-label.role-opening { background: var(--color-role-opening); color: white; }
.role-label.role-rising { background: var(--color-role-rising); color: white; }
.role-label.role-climax { background: var(--color-role-climax); color: white; }
.role-label.role-ending { background: var(--color-role-ending); color: white; }

.thread-chip span {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.thread-chip input:checked + span {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}
</style>
