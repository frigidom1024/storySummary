<template>
  <div class="timeline-view">
    <div v-for="threadId in orderedThreadIds" :key="threadId" class="timeline-row">
      <div class="thread-header">
        <span class="thread-name">{{ threadId }}</span>
      </div>
      <div class="thread-line">
        <TimelineNode
          v-for="node in nodesByThread[threadId]"
          :key="node.id"
          :node="node"
          @click="selectedNode = node"
        />
      </div>
    </div>
    <NodeDetail :node="selectedNode" @close="selectedNode = null" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { NarrativeNode } from '../api'
import TimelineNode from './TimelineNode.vue'
import NodeDetail from './NodeDetail.vue'

const props = defineProps<{
  nodesByThread: Record<string, NarrativeNode[]>
}>()

const selectedNode = ref<NarrativeNode | null>(null)

const orderedThreadIds = computed(() => {
  return Object.keys(props.nodesByThread).sort()
})
</script>

<style scoped>
.timeline-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.timeline-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thread-header {
  position: sticky;
  left: 0;
}

.thread-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 4px 8px;
  border-radius: 4px;
}

.thread-line {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 8px 0;
}
</style>
