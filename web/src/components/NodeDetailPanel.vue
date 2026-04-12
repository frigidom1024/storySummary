<template>
  <div class="node-detail-panel">
    <div class="panel-header">
      <div class="role-badge" :class="node.narrative_role">
        {{ roleText }}
      </div>
      <button class="close-btn" @click="emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <div class="panel-content">
      <div class="info-section">
        <label>场景</label>
        <p class="scene-text">{{ node.scene }}</p>
      </div>

      <div class="info-row">
        <div class="info-item">
          <label>地点</label>
          <span>{{ node.location || '-' }}</span>
        </div>
        <div class="info-item">
          <label>时间</label>
          <span>{{ node.scene_timing || '-' }}</span>
        </div>
      </div>

      <div class="info-section" v-if="node.characters?.length">
        <label>人物</label>
        <div class="character-tags">
          <span v-for="char in node.characters" :key="char.name" class="char-tag">
            {{ char.name }}
          </span>
        </div>
      </div>

      <div class="info-section" v-if="node.situation">
        <label>情况概述</label>
        <p>{{ node.situation }}</p>
      </div>

      <div class="info-section" v-if="node.turning_point">
        <label>转折点</label>
        <p class="turning-point">{{ node.turning_point }}</p>
      </div>

      <div class="info-row" v-if="node.emotional_arc">
        <div class="info-item">
          <label>情绪弧线</label>
          <span class="emotion-text">{{ node.emotional_arc }}</span>
        </div>
        <div class="info-item" v-if="node.mood_tone">
          <label>氛围</label>
          <span>{{ node.mood_tone }}</span>
        </div>
      </div>

      <div class="info-section" v-if="node.narrative_rhythm">
        <label>叙事节奏</label>
        <div class="rhythm-indicator">
          <span class="rhythm-bar" :class="node.narrative_rhythm"></span>
          <span class="rhythm-label">{{ node.narrative_rhythm }}</span>
        </div>
      </div>

      <div class="info-section" v-if="node.timeline_anchor">
        <label>时间锚点</label>
        <span class="time-anchor">{{ node.timeline_anchor }}</span>
      </div>

      <div class="info-section" v-if="node.thread_name">
        <label>叙事线</label>
        <span class="thread-badge">{{ node.thread_name }}</span>
      </div>

      <div class="info-section" v-if="node.is_time_jump">
        <label>时间跳转</label>
        <span class="time-jump">
          {{ node.jump_direction === 'past' ? '◀ 插叙' : '预叙 ▶' }}
          {{ node.jump_label || '' }}
        </span>
      </div>

      <div class="info-section" v-if="node.relationship_delta?.length">
        <label>关系变化</label>
        <div class="relationship-list">
          <div v-for="rel in node.relationship_delta" :key="rel.pair" class="relationship-item">
            <span class="pair">{{ rel.pair }}</span>
            <span class="delta">{{ rel.from_state }} → {{ rel.to_state }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NarrativeNode } from '../api'

const props = defineProps<{
  node: NarrativeNode
}>()

const emit = defineEmits<{
  close: []
}>()

const roleText = computed(() => {
  const map: Record<string, string> = {
    opening: '开场',
    rising: '发展',
    climax: '高潮',
    ending: '结尾'
  }
  return map[props.node.narrative_role] || '未知'
})
</script>

<style scoped>
.node-detail-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 360px;
  height: 100%;
  background: linear-gradient(180deg, #1a1f2e 0%, #0f1419 100%);
  border-left: 1px solid #2d3748;
  display: flex;
  flex-direction: column;
  z-index: 20;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid #2d3748;
}

.role-badge {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  color: white;
}

.role-badge.opening { background: #f59e0b; }
.role-badge.rising { background: #3b82f6; }
.role-badge.climax { background: #ef4444; box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); }
.role-badge.ending { background: #10b981; }

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.close-btn:hover {
  background: #2d3748;
  color: #f3f4f6;
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-section label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-section p {
  font-size: 14px;
  color: #e5e7eb;
  line-height: 1.6;
}

.scene-text {
  font-size: 15px !important;
  color: #f3f4f6 !important;
}

.turning-point {
  color: #fbbf24 !important;
  font-style: italic;
}

.info-row {
  display: flex;
  gap: 20px;
}

.info-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
}

.info-item span {
  font-size: 13px;
  color: #d1d5db;
}

.emotion-text {
  color: #f472b6 !important;
}

.character-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.char-tag {
  padding: 4px 10px;
  background: #2d3748;
  border-radius: 14px;
  font-size: 12px;
  color: #e5e7eb;
}

.rhythm-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rhythm-bar {
  width: 60px;
  height: 6px;
  border-radius: 3px;
  background: #374151;
}

.rhythm-bar.slow { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.rhythm-bar.steady { background: linear-gradient(90deg, #10b981, #34d399); }
.rhythm-bar.fast { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.rhythm-bar.pause { background: linear-gradient(90deg, #6b7280, #9ca3af); }

.rhythm-label {
  font-size: 12px;
  color: #9ca3af;
  text-transform: capitalize;
}

.time-anchor {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(168, 85, 247, 0.2);
  border: 1px solid #a855f7;
  border-radius: 14px;
  font-size: 12px;
  color: #c084fc;
}

.thread-badge {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid #3b82f6;
  border-radius: 14px;
  font-size: 12px;
  color: #60a5fa;
}

.time-jump {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(168, 85, 247, 0.2);
  border: 1px solid #a855f7;
  border-radius: 14px;
  font-size: 12px;
  color: #c084fc;
}

.relationship-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.relationship-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: #1f2937;
  border-radius: var(--radius-sm);
}

.pair {
  font-size: 13px;
  font-weight: 500;
  color: #e5e7eb;
}

.delta {
  font-size: 11px;
  color: #9ca3af;
}
</style>
