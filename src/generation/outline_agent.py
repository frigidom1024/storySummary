import os
from collections.abc import Callable

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
from src.generation.research_tools import ManuscriptResearchToolkit
from src.logging_config import debug
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode


class OutlineAgent:
    """负责生成全书级 outline（含伏笔与锚点）。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.3)

    async def build_outline(
        self,
        book_id: str,
        chunks: list[Chunk],
        nodes: list[NarrativeNode],
        progress_callback: Callable[[str], None] | None = None,
    ) -> str:
        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        chapter_summaries = await self._build_chapter_summaries(
            chunks, nodes, progress_callback=progress_callback
        )
        emit("[outline] 阶段1 完成；阶段2：全书 outline 优化（Agent + 工具，可能较久）…")
        tools = ManuscriptResearchToolkit.create_tools(book_id=book_id, chunks=chunks, nodes=nodes)

        system_prompt = """你是资深故事编辑，负责先产出全书级故事大纲，供后续章节写作 agent 使用。

要求：
- 你接收的是“逐章摘要初稿”，需要做全书级统筹优化。
- 必须忠于原始章节与叙事节点，不补写不存在的剧情。
- 输出应覆盖整体发展脉络，而不是零散章节摘要拼接。
- 明确标记关键位置：伏笔、回收点、时间锚点、关系转折、冲突升级点、高潮、收束。
- 需要能帮助“按章节增量写作”的 agent 在任意章节保持全局一致理解。
- 如果你需要获取原文信息来确认具体内容，请调用 lookup_original_text 和 vector_retrieve 工具。"""

        user_prompt = f"""你将拿到逐章摘要初稿。请先审查并纠偏，再输出结构化全书 outline。

逐章摘要初稿如下：
{chapter_summaries}
"""

        if self.debug_mode:
            debug("outline", "[OUTLINE] chapters={} nodes={}", len(chunks), len(nodes))

        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
            debug=self.debug_mode,
            name="outline-optimizer-agent",
        )
        response = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ]
            }
        )
        output = self._extract_output(response)
        if not output:
            raise ValueError("OutlineAgent returned empty response")
        emit("[outline] 阶段2 完成")
        return output

    @staticmethod
    def _format_node_for_summary(n: NarrativeNode) -> str:
        """仅用 scene / event_summary / characters 压成一行，人物为完整列表。"""
        scene = (n.scene or "").strip()
        event = (n.event_summary or "").strip()
        names = [
            c.name.strip()
            for c in n.characters
            if getattr(c, "name", None) and str(c.name).strip()
        ]
        if not scene and not event and not names:
            return ""
        scene_s = scene if scene else "（无）"
        event_s = event if event else "（无）"
        char_s = "、".join(names) if names else "（无）"
        return f"- 场景：{scene_s}；事件：{event_s}；人物：{char_s}"

    async def _build_chapter_summaries(
        self,
        chunks: list[Chunk],
        nodes: list[NarrativeNode],
        progress_callback: Callable[[str], None] | None = None,
    ) -> str:
        """阶段1：逐章摘要，产出章节初稿卡片。"""

        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        nodes_by_chunk: dict[str, list[NarrativeNode]] = {}
        for node in nodes:
            nodes_by_chunk.setdefault(node.parent_chunk_id, []).append(node)

        total = len(chunks)
        emit(f"[outline] 阶段1 逐章摘要：共 {total} 章，节点 {len(nodes)} 个")

        summaries: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            chapter_name = chunk.chapter or f"第{idx}章"
            emit(f"[outline] 摘要 {idx}/{total}：{chapter_name}（请求 LLM）…")
            chapter_nodes = nodes_by_chunk.get(chunk.id, [])
            node_lines: list[str] = []
            for n in chapter_nodes:
                line = self._format_node_for_summary(n)
                if line:
                    node_lines.append(line)
            node_text = "\n".join(node_lines) if node_lines else "- （无节点）"
            chunk_preview = chunk.text.replace("\n", " ")

            system_prompt = """你是章节摘要助手。只总结当前章节，不跨章推理。
- 忠于原文，不补写剧情。
- 输出紧凑，突出事件推进、关系变化、伏笔信号和章节亮点。"""
            user_prompt = f"""请为当前章节输出摘要卡片，使用以下结构：
1) 章节一段话概述
2) 关键事件


章节：{chapter_name}
节点线索：
{node_text}

原文：
{chunk_preview}
"""
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            chapter_summary = (response.content or "").strip()
            if not chapter_summary:
                chapter_summary = f"{chapter_name}\n- 摘要生成失败"
            summaries.append(f"## {chapter_name}\n{chapter_summary}")
            emit(f"[outline] 摘要 {idx}/{total}：{chapter_name} 完成")

        return "\n\n".join(summaries)

    def _extract_output(self, response: dict) -> str:
        messages = response.get("messages", []) if isinstance(response, dict) else []
        if not messages:
            return ""
        last = messages[-1]
        content = getattr(last, "content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            ).strip()
        return str(content).strip()
