"""Narrative Node Generator - 叙事节点生成器

Four-agent pipeline:
- Agent1: 叙事节点提取 (Narrative Beat Extraction)
- Agent2: 叙事线标记 (Thread Marking)
- Agent3: 有趣点发现 (Interesting Points Discovery)
- Agent4: 角色卡片维护 (Character Card Management)
"""
import logging
from dataclasses import dataclass
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterStateModel
from src.core.agents.agent1_extractor import Agent1Extractor, create_llm
from src.core.agents.agent2_thread_marker import Agent2ThreadMarker
from src.core.agents.agent3_interesting_finder import Agent3InterestingFinder
from src.core.agents.agent4_character_card import Agent4CharacterCard
from src.logging_config import debug

logger = logging.getLogger("story-summary")

# Re-export for backward compatibility
__all__ = ["create_llm"]


@dataclass
class PipelineConfig:
    enable_agent2: bool = True  # 叙事线标记
    enable_agent3: bool = True  # 有趣点发现
    enable_agent4: bool = True  # 角色卡片

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        import os
        return cls(
            enable_agent2=os.getenv("ENABLE_AGENT2", "true").lower() == "true",
            enable_agent3=os.getenv("ENABLE_AGENT3", "true").lower() == "true",
            enable_agent4=os.getenv("ENABLE_AGENT4", "true").lower() == "true",
        )


class NarrativeNodeGenerator:
    """Four-agent pipeline for generating narrative nodes from chunks."""

    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id
        self.model_name = model
        self.pipeline_config = PipelineConfig.from_env()

        # Initialize agents with book_id
        self.agent1 = Agent1Extractor(book_id=book_id, api_key=api_key, model=model)
        self.agent2 = Agent2ThreadMarker(api_key=api_key, book_id=book_id)
        self.agent3 = Agent3InterestingFinder(api_key=api_key, book_id=book_id)
        self.agent4 = Agent4CharacterCard(api_key=api_key, book_id=book_id)
        self.last_character_data: dict = {}

        # 设置 Agent2-4 的搜索函数（需要外部注入）
        self._search_fn = None
        self._get_thread_last_fn = None

    def set_search_fn(self, fn):
        """设置搜索函数，用于 Agent2-4 查询历史节点"""
        self._search_fn = fn
        self.agent2.set_search_fn(fn)
        self.agent3.set_search_fn(fn)
        self.agent4.set_search_fn(fn)

    def set_get_thread_last_fn(self, fn):
        """设置获取线程最后节点函数"""
        self._get_thread_last_fn = fn
        self.agent2.set_get_thread_last_fn(fn)
        self.agent3.set_get_thread_last_fn(fn)
        self.agent4.set_get_thread_last_fn(fn)

    async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
        """Generate narrative nodes from ONE chunk through the agent pipeline."""
        debug("node_generator", "[Chunk {}] Starting pipeline", chunk.id)

        # === Agent1: 叙事节点提取 ===
        debug("node_generator", "Agent1: Extracting narrative beats")
        beats = await self.agent1.extract(chunk)
        debug("node_generator", "Agent1: Extracted {} beats", len(beats))

        if not beats:
            return []

        # 构建上下文
        context = {
            "chunk_id": chunk.id,
            "chunk_text": chunk.text,
            "chunk_order": chunk.order,
        }

        # === Agent2: 叙事线标记 ===
        if self.pipeline_config.enable_agent2:
            debug("node_generator", "Agent2: Marking threads for {} nodes", len(beats))
            beats = await self.agent2.mark(beats, context)
            debug("node_generator", "Agent2: Thread marking complete")
            for i, b in enumerate(beats):
                debug("node_generator", "  beat[{}] id={} thread_id={}", i, b.get('id'), b.get('thread_id'))

        # === Agent3: 有趣点发现 ===
        if self.pipeline_config.enable_agent3:
            debug("node_generator", "Agent3: Finding interesting points for {} nodes", len(beats))
            beats = await self.agent3.find(beats, context)
            debug("node_generator", "Agent3: Interesting points found")
            for i, b in enumerate(beats):
                debug("node_generator", "  beat[{}] id={} discussion_prompts={}",
                      i, b.get('id'), len(b.get('discussion_prompts', [])))

        # === Agent4: 角色卡片维护 ===
        if self.pipeline_config.enable_agent4:
            debug("node_generator", "Agent4: Processing character cards for {} nodes", len(beats))
            await self.agent4.process_nodes(beats, context)
            char_count = len(self.agent4.characters)
            debug("node_generator", "Agent4: Now tracking {} characters", char_count)
            for char_name, card in self.agent4.characters.items():
                debug("node_generator", "  char={} appearances={} relationships={}",
                      char_name, card.total_appearances, list(card.relationships.keys()))
            self.last_character_data = {
                "characters": self.agent4.get_all_characters(),
                "relationship_graph": self.agent4.get_relationship_graph(),
            }

        # === 转换为 NarrativeNode 对象 ===
        nodes = []
        for validated in beats:
            valid_characters = [
                CharacterStateModel(name=c.get('name', ''))
                for c in validated.get('characters', []) if c.get('name')
            ]

            # Use id from validated beat (constructed by agent1)
            node_id = validated['id']

            node = NarrativeNode(
                id=node_id,
                beat_index=validated['beat_index'],
                scene=validated['scene'],
                location=validated.get('location', ''),
                scene_timing=validated.get('scene_timing', ''),
                characters=valid_characters,
                event_summary=validated.get('event_summary', ''),
                situation=validated.get('situation', ''),
                turning_point=validated.get('turning_point', ''),
                importance=validated.get('importance', 0.5),
                time_label=validated.get('time_label', ''),
                thread_id=validated.get('thread_id', 'main'),
                thread_name=validated.get('thread_name', ''),
                thread_prev_node_id=validated.get('thread_prev_node_id', ''),
                thread_next_node_id=validated.get('thread_next_node_id', ''),
                discussion_prompts=validated.get('discussion_prompts', []),
                parent_chunk_id=chunk.id
            )
            nodes.append(node)

        debug("node_generator", "[Chunk {}] Generated {} nodes", chunk.id, len(nodes))
        return nodes

    @staticmethod
    def link_nodes_globally(nodes: list[NarrativeNode], chunks: list[Chunk]) -> list[NarrativeNode]:
        """全局链接所有 nodes 的 prev/next 关系，确保跨 chunk 链接正确。

        规则：
        - 按 chunk 顺序和 beat_index 排序
        - 同一个 thread 内，第一个 node 的 prev 为空，最后一个 node 的 next 为空
        - 跨 chunk 时，下一个 chunk 的第一个 node 的 prev 指向上一 chunk 的最后一个 node
        """
        if not nodes:
            return nodes

        # 按 parent_chunk_id 和 beat_index 排序
        def sort_key(n: NarrativeNode) -> tuple:
            chunk_order = 0
            for i, c in enumerate(chunks):
                if c.id == n.parent_chunk_id:
                    chunk_order = i
                    break
            return (chunk_order, n.beat_index)

        sorted_nodes = sorted(nodes, key=sort_key)

        # 按 thread 分组
        threads: dict[str, list[NarrativeNode]] = {}
        for node in sorted_nodes:
            thread_id = node.thread_id or "main"
            threads.setdefault(thread_id, []).append(node)

        # 链接每个 thread
        for thread_id, thread_nodes in threads.items():
            for i, node in enumerate(thread_nodes):
                if i == 0:
                    node.thread_prev_node_id = ""
                else:
                    node.thread_prev_node_id = thread_nodes[i - 1].id

                if i == len(thread_nodes) - 1:
                    node.thread_next_node_id = ""
                else:
                    node.thread_next_node_id = thread_nodes[i + 1].id

        return sorted_nodes
