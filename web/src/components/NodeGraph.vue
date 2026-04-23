<template>
  <div class="node-graph" ref="containerRef">
    <svg ref="svgRef" class="graph-svg"></svg>

    <div class="graph-controls">
      <button class="control-btn" @click="zoomIn">+</button>
      <button class="control-btn" @click="zoomOut">-</button>
      <button class="control-btn" @click="resetView">⟲</button>
    </div>

    <div class="graph-legend">
      <div class="legend-item"><span class="legend-dot opening"></span>开场</div>
      <div class="legend-item"><span class="legend-dot rising"></span>发展</div>
      <div class="legend-item"><span class="legend-dot climax"></span>高潮</div>
      <div class="legend-item"><span class="legend-dot ending"></span>结尾</div>
    </div>

    <Transition name="slide">
      <NodeDetailPanel v-if="selectedNode" :node="selectedNode" @close="selectedNode = null" />
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import type { NarrativeNode } from '../api'
import NodeDetailPanel from './NodeDetailPanel.vue'

defineOptions({ name: 'NodeGraph' })

const props = defineProps<{
  nodes: NarrativeNode[]
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)
const selectedNode = ref<NarrativeNode | null>(null)

let scale = 1
let translateX = 0
let translateY = 0
let isDragging = false
let startX = 0
let startY = 0

const roleColors: Record<string, string> = {
  opening: '#f59e0b',
  rising: '#3b82f6',
  climax: '#ef4444',
  ending: '#10b981',
}

function initGraph() {
  if (!svgRef.value || !containerRef.value || props.nodes.length === 0) return

  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight
  const svg = d3.select(svgRef.value)

  svg.selectAll('*').remove()
  svg.attr('width', width).attr('height', height)

  // Background
  svg.append('rect')
    .attr('width', width)
    .attr('height', height)
    .attr('fill', '#0f1419')

  const g = svg.append('g').attr('class', 'content')

  // Links
  const nodeMap = new Map(props.nodes.map(n => [n.id, n]))
  const links = props.nodes
    .filter(n => n.prev_node_id && nodeMap.has(n.prev_node_id))
    .map(n => ({ source: nodeMap.get(n.prev_node_id)!, target: n }))

  g.append('g').attr('class', 'links')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', '#4b5563')
    .attr('stroke-width', 2)

  // Nodes
  const nodeGroups = g.append('g').attr('class', 'nodes')
    .selectAll('g')
    .data(props.nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .style('cursor', 'pointer')

  nodeGroups.append('circle')
    .attr('r', d => 18 + (d.importance || 0.5) * 8)  // Size based on importance
    .attr('fill', d => roleColors[d.narrative_role] || '#3b82f6')
    .attr('stroke', d => d.is_time_jump ? '#f59e0b' : '#1f2937')
    .attr('stroke-width', d => d.is_time_jump ? 3 : 2)

  nodeGroups.append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'white')
    .attr('font-size', '12px')
    .attr('font-weight', '600')
    .text(d => d.beat_index + 1)

  nodeGroups.append('text')
    .attr('y', 36)
    .attr('text-anchor', 'middle')
    .attr('fill', '#9ca3af')
    .attr('font-size', '10px')
    .text(d => (d.location || '未知').slice(0, 5))

  // Click
  nodeGroups.on('click', (event, d) => {
    event.stopPropagation()
    selectedNode.value = d
  })

  // Simple circle layout
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) * 0.35

  props.nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / props.nodes.length - Math.PI / 2
    node.x = centerX + radius * Math.cos(angle)
    node.y = centerY + radius * Math.sin(angle)
  })

  nodeGroups.attr('transform', d => `translate(${d.x},${d.y})`)

  // Update links
  g.select('.links').selectAll('line')
    .attr('x1', (d: any) => d.source.x)
    .attr('y1', (d: any) => d.source.y)
    .attr('x2', (d: any) => d.target.x)
    .attr('y2', (d: any) => d.target.y)

  // Pan
  svg.on('mousedown', (event) => {
    isDragging = true
    startX = event.clientX - translateX
    startY = event.clientY - translateY
  })
  .on('mousemove', (event) => {
    if (!isDragging) return
    translateX = event.clientX - startX
    translateY = event.clientY - startY
    g.attr('transform', `translate(${translateX},${translateY}) scale(${scale})`)
  })
  .on('mouseup', () => { isDragging = false })
  .on('mouseleave', () => { isDragging = false })

  // Wheel zoom
  svg.on('wheel', (event) => {
    event.preventDefault()
    const delta = event.deltaY > 0 ? 0.9 : 1.1
    scale *= delta
    scale = Math.max(0.3, Math.min(3, scale))
    g.attr('transform', `translate(${translateX},${translateY}) scale(${scale})`)
  })
}

function zoomIn() {
  scale = Math.min(3, scale * 1.2)
  if (!svgRef.value) return
  d3.select(svgRef.value).select('g').attr('transform', `translate(${translateX},${translateY}) scale(${scale})`)
}

function zoomOut() {
  scale = Math.max(0.3, scale / 1.2)
  if (!svgRef.value) return
  d3.select(svgRef.value).select('g').attr('transform', `translate(${translateX},${translateY}) scale(${scale})`)
}

function resetView() {
  scale = 1
  translateX = 0
  translateY = 0
  if (!svgRef.value) return
  d3.select(svgRef.value).select('g').attr('transform', `translate(0,0) scale(1)`)
}

watch(() => props.nodes, () => nextTick(initGraph), { deep: true })
onMounted(() => nextTick(initGraph))
</script>

<style scoped>
.node-graph {
  position: relative;
  width: 100%;
  height: 600px;
  background: #0f1419;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.graph-svg {
  width: 100%;
  height: 100%;
}

.graph-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10;
}

.control-btn {
  width: 36px;
  height: 36px;
  border: 1px solid #374151;
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.9);
  color: #9ca3af;
  font-size: 18px;
  cursor: pointer;
}

.control-btn:hover {
  background: rgba(55, 65, 81, 0.9);
  color: #fff;
}

.graph-legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  display: flex;
  gap: 16px;
  padding: 10px 16px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid #1f2937;
  border-radius: var(--radius-md);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #d1d5db;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.legend-dot.opening { background: #f59e0b; }
.legend-dot.rising { background: #3b82f6; }
.legend-dot.climax { background: #ef4444; }
.legend-dot.ending { background: #10b981; }

.slide-enter-active, .slide-leave-active { transition: transform 0.3s; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>
