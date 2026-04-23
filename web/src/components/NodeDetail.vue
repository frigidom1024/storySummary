<template>
  <Teleport to="body">
    <div v-if="node" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-content">
        <button class="close-btn" @click="emit('close')">x</button>
        <h2 class="modal-title">{{ node.scene }}</h2>

        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-row">
            <span class="label">ID:</span>
            <span>{{ node.id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">叙事角色:</span>
            <span class="role-tag" :class="`role-${node.narrative_role}`">
              {{ node.narrative_role }}
            </span>
          </div>
          <div class="detail-row">
            <span class="label">叙事线:</span>
            <span>{{ node.thread_name || node.thread_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">时间顺序:</span>
            <span>{{ node.timeline_order }}</span>
          </div>
          <div v-if="node.timeline_anchor" class="detail-row">
            <span class="label">时间锚点:</span>
            <span>{{ node.timeline_anchor }}</span>
          </div>
        </div>

        <div v-if="node.situation" class="detail-section">
          <h4>核心情境</h4>
          <p>{{ node.situation }}</p>
        </div>

        <div v-if="node.turning_point" class="detail-section">
          <h4>转折点</h4>
          <p>{{ node.turning_point }}</p>
        </div>

        <div v-if="node.emotional_arc" class="detail-section">
          <h4>情绪弧</h4>
          <p>{{ node.emotional_arc }}</p>
        </div>

        <div v-if="node.importance" class="detail-section">
          <h4>重要性</h4>
          <div class="importance-bar">
            <div class="importance-fill" :style="{ width: `${node.importance * 100}%` }"></div>
          </div>
          <span class="importance-value">{{ (node.importance * 100).toFixed(0) }}%</span>
        </div>

        <div v-if="node.characters?.length" class="detail-section">
          <h4>角色</h4>
          <div v-for="char in node.characters" :key="char.name" class="character-item">
            <span class="char-name">{{ char.name }}</span>
            <span v-if="char.state_before" class="char-state">{{ char.state_before }}</span>
          </div>
        </div>

        <div v-if="node.interactions?.length" class="detail-section">
          <h4>角色交互</h4>
          <div v-for="interaction in node.interactions" :key="interaction.target" class="interaction-item">
            <span class="interaction-target">{{ node.characters?.[0]?.name || '?' }}</span>
            <span class="interaction-arrow">→</span>
            <span class="interaction-target">{{ interaction.target }}</span>
            <span class="interaction-type" :class="`type-${interaction.type}`">{{ interaction.type }}</span>
          </div>
        </div>

        <div v-if="node.relationship_delta?.length" class="detail-section">
          <h4>关系变化</h4>
          <div v-for="rel in node.relationship_delta" :key="rel.pair" class="rel-item">
            <span class="rel-pair">{{ rel.pair }}</span>
            <span>{{ rel.from_state }} → {{ rel.to_state }}</span>
          </div>
        </div>

        <div v-if="node.mood_tone" class="detail-section">
          <h4>氛围</h4>
          <p>{{ node.mood_tone }}</p>
        </div>

        <div v-if="node.narrative_rhythm" class="detail-section">
          <h4>节奏</h4>
          <p>{{ node.narrative_rhythm }}</p>
        </div>

        <div v-if="node.discussion_prompts?.length" class="detail-section">
          <h4>讨论锚点</h4>
          <ul>
            <li v-for="(prompt, i) in node.discussion_prompts" :key="i">{{ prompt }}</li>
          </ul>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import type { NarrativeNode } from '../api'

defineProps<{ node: NarrativeNode | null }>()
const emit = defineEmits<{ close: [] }>()
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-surface);
  border-radius: 12px;
  padding: 24px;
  max-width: 560px;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-right: 24px;
}

.detail-section {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.detail-row {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 14px;
}

.detail-row .label {
  color: var(--color-text-secondary);
}

.role-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: white;
}

.role-opening { background: var(--color-role-opening); }
.role-rising { background: var(--color-role-rising); }
.role-climax { background: var(--color-role-climax); }
.role-ending { background: var(--color-role-ending); }

.character-item,
.rel-item {
  font-size: 14px;
  margin-bottom: 4px;
}

.char-name {
  font-weight: 500;
  margin-right: 8px;
}

.importance-bar {
  height: 8px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}

.importance-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  border-radius: 4px;
  transition: width 0.3s;
}

.importance-value {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.interaction-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
}

.interaction-target {
  font-weight: 500;
}

.interaction-arrow {
  color: var(--color-text-secondary);
}

.interaction-type {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: white;
}

.interaction-type.type-tension { background: var(--color-destructive); }
.interaction-type.type-support { background: var(--color-role-ending); }
.interaction-type.type-neutral { background: var(--color-muted); }

.char-state,
.rel-pair {
  color: var(--color-text-secondary);
}
</style>
