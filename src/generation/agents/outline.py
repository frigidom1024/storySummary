import json
import os
from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
from src.logging_config import debug
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode


class OutlineAgent:
    """负责生成全书级 outline（含伏笔与锚点）。

    流程：
    1. 阶段1：批量章节摘要（每批5章）
    2. 阶段2a：基于章节摘要构建故事梗概（自然语言）
    2. 阶段2b：基于章节摘要构建口播稿Outline
    """

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
    ) -> tuple[str, str]:
        """返回 (story_synopsis, manuscript_outline_json) 元组，调用者按需取用。"""
        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        has_reference = "有" if reference_script else "无"
        emit(f"[outline] 阶段1 开始（参考口播稿：{has_reference}）...")

        # 过滤：只保留正文类型的章节
        story_chunks = [c for c in chunks if c.content_type == "story_content"]
        emit(f"[outline] 过滤后正文章节：{len(story_chunks)}/{len(chunks)}")

        nodes_by_chunk: dict[str, list[NarrativeNode]] = {}
        for node in nodes:
            nodes_by_chunk.setdefault(node.parent_chunk_id, []).append(node)

        # 阶段1：批量章节摘要
        chapter_summaries = await self.batch_summarize_chapters(
            story_chunks, nodes_by_chunk, progress_callback=progress_callback
        )
        emit("[outline] 阶段1 完成")

        # 阶段2a：构建故事梗概
        emit("[outline] 阶段2a：构建故事梗概...")
        story_synopsis = await self.build_story_synopsis(
            chapter_summaries, progress_callback=progress_callback
        )
        emit("[outline] 阶段2a 完成")

        # 阶段2b：构建口播稿Outline
        emit("[outline] 阶段2b：构建口播稿Outline...")
        manuscript_outline = await self.build_manuscript_outline(
            chapter_summaries, story_chunks, reference_script, progress_callback=progress_callback
        )
        emit("[outline] 阶段2b 完成")

        # 返回元组，调用者按需取用
        manuscript_outline_json = json.dumps(manuscript_outline, ensure_ascii=False)
        return story_synopsis, manuscript_outline_json

    async def build_story_synopsis(
        self,
        chapter_summaries: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> str:
        """阶段2a：基于章节摘要用自然语言写完整故事梗概。"""

        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        system_prompt = """你是资深故事编辑，擅长用流畅的自然语言讲述完整故事。

## 你的任务
基于章节摘要，用连贯的自然语言写一段完整的故事梗概。

## 要求
1. 故事梗概应该像讲故事一样娓娓道来，不是干巴巴的要点罗列
2. 必须涵盖：核心人物身份、核心冲突、关键情节点、结局
3. 使用"很久以前""有一天""最终"等叙事连接词让故事流畅
4. 突出故事的转折点和戏剧性时刻
5. 严格忠于原始章节摘要，不补写不存在的剧情
6. 长度适中（300-600字），足够清晰又不过于细节
7. 直接输出故事梗概正文，不要包含任何标记或说明"""

        user_prompt = f"""请基于以下章节摘要，用自然语言写一段完整的故事梗概：

{chapter_summaries}

请直接输出故事梗概正文，不要包含任何其他内容。"""

        response = await self.llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        output = self._extract_output(response)
        if not output:
            raise ValueError("build_story_synopsis returned empty response")
        emit(f"[outline] 故事梗概生成完成（{len(output)}字）")
        return output

    async def build_manuscript_outline(
        self,
        chapter_summaries: str,
        chunks: list[Chunk],
        reference_script: str | None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """阶段2b：构建口播稿Outline结构。"""

        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        # 如果有参考口播稿，提取风格描述用于调整 tone
        reference_style = ""
        if reference_script:
            reference_style = f"\n\n## 参考口播稿风格\n请学习以下口播稿的风格特点，并在 metadata.tone 中体现：\n{reference_script[:2000]}..."

        system_prompt = f"""你是资深故事编辑，负责生成结构化口播稿大纲。

## 你的任务
根据章节摘要，规划口播稿结构（manuscript_outline）。

## 输出格式
必须输出有效的 JSON 字符串，格式如下：
{{
  "manuscript_outline": [
    {{"section": "开篇介绍", "type": "author_intro", "description": "..."}},
    {{"section": "第X章", "type": "story_content", "chapter": X, "description": "..."}},
    {{"section": "思考与总结", "type": "reflection", "description": "..."}}
  ],
  "metadata": {{
    "tone": "口语化、亲切、故事感"
  }}
}}

## Section Type 分类
- author_intro: 作者/书籍介绍
- story_content: 故事情节内容（必须包含 chapter 编号）
- reflection: 思考、总结、感悟

## 要求
- 必须忠于原始章节与叙事节点，不补写不存在的剧情
- manuscript_outline 必须覆盖所有章节
- 如果有参考口播稿，学习其风格并调整 metadata.tone{reference_style}
- 直接输出 JSON，不要包含任何其他内容"""

        user_prompt = f"""你将拿到逐章摘要初稿。请先审查并纠偏，再输出口播稿结构 JSON。

逐章摘要初稿如下：
{chapter_summaries}

请直接输出 JSON，不要包含任何其他内容。"""

        response = await self.llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        output = self._extract_output(response)
        if not output:
            raise ValueError("build_manuscript_outline returned empty response")

        # 验证 JSON 可解析
        try:
            parsed = json.loads(output)
            manuscript_outline = parsed.get("manuscript_outline", [])
        except json.JSONDecodeError:
            raise ValueError("build_manuscript_outline did not return valid JSON: " + output[:200])

        # 给 story_content 类型添加 chunk_id 字段
        for chunk in chunks:
            chapter_num = chunk.order + 1
            for item in manuscript_outline:
                if item.get("type") == "story_content" and item.get("chapter") == chapter_num:
                    item["chunk_id"] = chunk.id
                    break

        emit(f"[outline] 口播稿Outline生成完成（{len(manuscript_outline)}个节点）")
        return manuscript_outline

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
        nodes_by_chunk: dict[str, list[NarrativeNode]],
        progress_callback: Callable[[str], None] | None = None,
    ) -> str:
        """阶段1：批量摘要，每批5章。"""

        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        total = len(chunks)
        emit(f"[outline] 阶段1 批量摘要：共 {total} 章")

        # 按5章一批分组
        batch_size = 5
        summaries: list[str] = []

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_chunks = chunks[batch_start:batch_end]
            n = len(batch_chunks)

            emit(f"[outline] 批量摘要 {batch_start + 1}-{batch_end}/{total}（请求 LLM）…")

            # 构建批量prompt
            chapter_blocks: list[str] = []
            for i, chunk in enumerate(batch_chunks):
                chapter_num = batch_start + i + 1
                chapter_name = chunk.chapter or f"第{chapter_num}章"
                chapter_nodes = nodes_by_chunk.get(chunk.id, [])
                node_lines: list[str] = []
                for n_node in chapter_nodes:
                    line = self._format_node_for_summary(n_node)
                    if line:
                        node_lines.append(line)
                node_text = "\n".join(node_lines) if node_lines else "- （无节点）"
                chapter_blocks.append(f"""## {chapter_name}
节点线索：
{node_text}
原文内容：
{chunk.text}""")

            system_prompt = """你是章节摘要助手。只总结当前章节，不跨章推理。
- 忠于原文，不补写剧情。
- 输出紧凑，突出事件推进、关系变化、伏笔信号和章节亮点。
- 每个章节输出格式：## 第X章: xxx\\n[摘要内容]"""
            user_prompt = f"请为以下 {n} 章生成摘要，输出 {n} 个独立章节摘要块：\n\n" + "\n\n".join(chapter_blocks)

            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            batch_summary = (response.content or "").strip()
            if not batch_summary:
                batch_summary = "\n\n".join(
                    f"## {chunk.chapter or f'第{batch_start + batch_chunks.index(chunk) + 1}章'}\n- 摘要生成失败"
                    for chunk in batch_chunks
                )
            summaries.append(batch_summary)
            emit(f"[outline] 批量摘要 {batch_start + 1}-{batch_end}/{total} 完成")

        return "\n\n".join(summaries)

    def _extract_output(self, response) -> str:
        # 支持 dict 格式（兼容旧代码）和 AIMessage 对象
        if hasattr(response, "content"):
            # AIMessage 或类似对象
            content = response.content
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                return "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content
                ).strip()
            return str(content).strip()
        # dict 格式兼容
        messages = response.get("messages", []) if isinstance(response, dict) else []
        if not messages:
            # 调试信息
            debug("outline", "[OUTLINE] _extract_output: no messages, response type={}", type(response))
            if self.debug_mode and hasattr(response, "content"):
                debug("outline", "[OUTLINE] response.content={}", getattr(response, "content", None))
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