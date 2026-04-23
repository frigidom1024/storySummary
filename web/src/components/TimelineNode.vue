<template>
  <div
    class="timeline-node"
    :class="[`role-${node.narrative_role}`, { 'has-jump': node.is_time_jump }]"
    @click="emit('click', node)"
  >
    <div class="node-header">
      <span class="role-tag" :class="`role-${node.narrative_role}`">
        {{ node.narrative_role }}
      </span>
      <span v-if="node.is_time_jump" class="jump-tag">
        {{ node.jump_direction === 'past' ? '插叙' : '预叙' }}
      </span>
    </div>
    <div class="node-scene">{{ node.scene || '未知场景' }}</div>
    <div class="node-meta">
      <span v-if="node.location">{{ node.location }}</span>
      <span v-if="node.scene_timing">{{ node.scene_timing }}</span>
    </div>
    <div class="node-characters">
      {{ characterNames }}
    </div>
    <div v-if="node.emotional_arc" class="node-emotion">
      {{ node.emotional_arc }}
    </div>
    <div v-if="node.timeline_anchor" class="node-anchor">
      {{ node.timeline_anchor }}
    </div>
    <div v-if="node.importance !== undefined" class="node-importance">
      <div class="importance-bar-timeline">
        <div class="importance-fill-timeline" :style="{ width: `${node.importance * 100}%` }"></div>
      </div>
    </div>
    <div v-if="node.interactions?.length" class="node-interactions">
      <span v-for="(interaction, idx) in node.interactions.slice(0, 2)" :key="idx" class="interaction-dot" :class="`type-${interaction.type}`" :title="`${interaction.target}: ${interaction.type}`"></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NarrativeNode } from '../api'

const props = defineProps<{ node: NarrativeNode }>()
const emit = defineEmits<{ click: [node: NarrativeNode] }>()

const characterNames = computed(() =>
  props.node.characters?.map((c) => c.name).join('、') || ''
)
</script>

<style scoped>
.timeline-node {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
  min-width: 180px;
  max-width: 220px;
}

.timeline-node:hover {
  box-shadow: var(--shadow);
}

.node-header {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.role-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  color: white;
}

.role-opening { background: var(--color-role-opening); }
.role-rising { background: var(--color-role-rising); }
.role-climax { background: var(--color-role-climax); }
.role-ending { background: var(--color-role-ending); }

.jump-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  background: #9333ea;
  color: white;
}

.node-scene {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  line-height: 1.3;
}

.node-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.node-characters {
  font-size: 12px;
  color: var(--color-text);
  margin-bottom: 4px;
}

.node-emotion {
  font-size: 11px;
  color: var(--color-text-secondary);
  font-style: italic;
}

.node-anchor {
  margin-top: 6px;
  font-size: 11px;
  color: #9333ea;
  font-weight: 500;
}

.node-importance {
  margin-top: 6px;
}

.importance-bar-timeline {
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.importance-fill-timeline {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
}

.node-interactions {
  margin-top: 6px;
  display: flex;
  gap: 4px;
}

.interaction-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.interaction-dot.type-tension { background: #ef4444; }
.interaction-dot.type-support { background: #10b981; }
.interaction-dot.type-neutral { background: #6b7280; }
</style>
