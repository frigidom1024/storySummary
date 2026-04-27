import json
import os
from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
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
        reference_script: str | None = None,
    ) -> str:  # 返回 JSON 字符串
        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        chapter_summaries = await self.batch_summarize_chapters(
            chunks, nodes, progress_callback=progress_callback
        )
        emit("[outline] 阶段1 完成；阶段2：全书 outline 优化（直接 LLM JSON 输出）…")

        system_prompt = """你是资深故事编辑，负责生成结构化口播稿大纲。

## 你的任务
1. 根据章节摘要提炼全书故事梗概（story_synopsis）
2. 规划口播稿结构（manuscript_outline）

## 输出格式
必须输出有效的 JSON 字符串，格式如下：
{
  "story_synopsis": "全文故事情节摘要，包含核心人物、核心冲突、关键转折、结局",
  "manuscript_outline": [
    {"section": "开篇介绍", "type": "author_intro", "description": "..."},
    {"section": "第X章", "type": "story_content", "chapter": X, "description": "..."},
    {"section": "思考与总结", "type": "reflection", "description": "..."}
  ],
  "metadata": {
    "total_sections": 15,
    "estimated_duration": "约2小时",
    "tone": "口语化、亲切、故事感"
  }
}

## Section Type 分类
- author_intro: 作者/书籍介绍
- story_content: 故事情节内容（必须包含 chapter 编号）
- reflection: 思考、总结、感悟

## 要求
- 必须忠于原始章节与叙事节点，不补写不存在的剧情
- manuscript_outline 必须覆盖所有章节
- 如果有参考口播稿，学习其风格并调整 metadata.tone
- 直接输出 JSON，不要包含任何其他内容"""

        user_prompt = f"""你将拿到逐章摘要初稿。请先审查并纠偏，再输出结构化 JSON 大纲。

逐章摘要初稿如下：
{chapter_summaries}

请直接输出 JSON，不要包含任何其他内容。"""

        if self.debug_mode:
            debug("outline", "[OUTLINE] chapters={} nodes={}", len(chunks), len(nodes))

        response = await self.llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        output = self._extract_output(response)
        if not output:
            raise ValueError("OutlineAgent returned empty response")

        # 尝试解析为 JSON
        try:
            json.loads(output)
        except json.JSONDecodeError:
            raise ValueError("OutlineAgent did not return valid JSON")

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

    async def batch_summarize_chapters(
        self,
        chunks: list[Chunk],
        nodes: list[NarrativeNode],
        progress_callback: Callable[[str], None] | None = None,
    ) -> str:
        """阶段1：批量摘要，每批5章调用一次 LLM。"""

        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        nodes_by_chunk: dict[str, list[NarrativeNode]] = {}
        for node in nodes:
            nodes_by_chunk.setdefault(node.parent_chunk_id, []).append(node)

        total = len(chunks)
        emit(f"[outline] 阶段1 批量摘要：共 {total} 章，节点 {len(nodes)} 个")

        # Build node_text for each chunk
        chunk_node_info: dict[str, tuple[str, str]] = {}
        for idx, chunk in enumerate(chunks, start=1):
            chapter_name = chunk.chapter or f"第{idx}章"
            chapter_nodes = nodes_by_chunk.get(chunk.id, [])
            node_lines: list[str] = []
            for n in chapter_nodes:
                line = self._format_node_for_summary(n)
                if line:
                    node_lines.append(line)
            node_text = "\n".join(node_lines) if node_lines else "- （无节点）"
            chunk_node_info[chunk.id] = (chapter_name, node_text)

        # Group into batches of 5
        batch_size = 5
        batches: list[list[Chunk]] = []
        for i in range(0, len(chunks), batch_size):
            batches.append(chunks[i : i + batch_size])

        summaries: list[str] = []
        for batch_idx, batch in enumerate(batches, start=1):
            emit(f"[outline] 批量摘要 {batch_idx}/{len(batches)}：处理 {len(batch)} 章（请求 LLM）…")

            # Build batch prompt
            chapter_blocks: list[str] = []
            for chunk in batch:
                chapter_name, node_text = chunk_node_info[chunk.id]
                chapter_blocks.append(
                    f"## 第{chapter_name}\n"
                    f"节点线索：\n"
                    f"{node_text}\n"
                    f"原文内容：\n"
                    f"{chunk.text}\n"
                )

            system_prompt = """你是章节摘要助手。只总结当前章节，不跨章推理。
- 忠于原文，不补写剧情。
- 输出紧凑，突出事件推进、关系变化、伏笔信号和章节亮点。
- 每个章节输出格式：## 第X章: xxx\n[摘要内容]"""

            user_prompt = f"请为以下 {len(batch)} 章生成摘要，输出 {len(batch)} 个独立章节摘要块：\n\n"
            user_prompt += "\n\n".join(chapter_blocks)

            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            batch_result = (response.content or "").strip()
            if batch_result:
                summaries.append(batch_result)
            emit(f"[outline] 批量摘要 {batch_idx}/{len(batches)}：完成")

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