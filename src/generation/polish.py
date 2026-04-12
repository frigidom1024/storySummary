import os
import json
from typing import TYPE_CHECKING, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from src.core.node_generator import create_llm

if TYPE_CHECKING:
    from src.models.chunk import Chunk
    from src.generation.models import ChapterDraft


POLISH_SYSTEM_PROMPT = """你是一个播客稿编辑。你的任务是对多章节播客稿进行逐章润色。

## 润色要求

1. **消除重复**：各章节间可能重复的观点、表述要合并/删除
2. **统一语气**：确保口语化风格一致，没有书面语残留
3. **强化过渡**：检查章与章之间的过渡句是否自然
4. **升华结尾**：最后一章的结尾要有力量感，适当呼应全书主题
5. **个人思考**：确保每个章节都有个人思考，不是纯情节复述
6. **事实核实**：对照原文确保情节描述准确

## 工具使用

你可以使用 get_chunk_context 工具查看任意章节的原文。但注意：
- 对话中只能保留一个完整章节的原文
- 加载新章节时，旧章节会被丢弃
- 先读完所有章节，再决定是否需要回头核实

## 输出格式

对于每个章节，按以下格式输出润色结果：
【第X章润色】
<润色后的内容>

最后输出完整稿子：
【完整稿子】
<所有章节合并后的完整润色稿>
"""


class ChunkContextTool:
    """上下文工具，控制在对话中只保留一个 chunk 的原文"""

    def __init__(self, chunks: dict):
        self.chunks = chunks
        self.current_chunk_id: Optional[str] = None
        self.current_chunk_text: Optional[str] = None

    def get_chunk_text(self, chunk_id: str) -> str:
        """获取章节原文，同时丢弃旧的上下文"""
        # 加载新章节，丢弃旧章节
        self.current_chunk_id = chunk_id
        self.current_chunk_text = None  # 清空旧上下文

        chunk = self.chunks.get(chunk_id)
        if not chunk:
            return f"[错误] 未找到章节: {chunk_id}"

        # 返回完整原文
        self.current_chunk_text = chunk.text
        title = chunk.chapter or f"章节{chunk.order + 1}"

        return f"【{title}】\n\n{chunk.text}"

    def get_context_summary(self) -> str:
        """获取当前上下文摘要（用于 AI 参考）"""
        if self.current_chunk_id and self.current_chunk_text:
            preview = self.current_chunk_text[:500]
            return f"[当前加载的章节: {self.current_chunk_id}]\n{preview}..."
        return "[无加载的章节原文]"


@tool
def get_chunk_context(chunk_id: str) -> str:
    """获取指定章节的原始文本内容。

    Args:
        chunk_id: 章节ID

    Returns:
        该章节的完整原文内容
    """
    # 实际实现通过 ChunkContextTool
    return "[请通过 ChunkContextTool 获取]"  # 占位符


class PolishPass:
    """润色器 - 支持工具调用，单章节上下文"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def polish(
        self,
        drafts: list["ChapterDraft"],
        chunks: dict[str, "Chunk"],
    ) -> str:
        """
        润色完整草稿

        Args:
            drafts: 章节草稿列表
            chunks: chunk_id -> Chunk 映射
        """
        tool_handler = ChunkContextTool(chunks)

        # 构建章节索引（不含原文）
        chapters_index = self._build_chapters_index(drafts, chunks)
        chapters_text = self._build_chapters_text(drafts)

        prompt = f"""## 章节索引
{chapters_index}

## 章节稿子
{chapters_text}

请先阅读所有章节稿子，然后逐章使用 get_chunk_context 工具对照原文进行润色。"""

        messages = [
            SystemMessage(content=POLISH_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        # 绑定工具
        llm_with_tools = self.llm.bind_tools(
            [get_chunk_context],
            parallel_tool_calls=False
        )

        # 工具调用循环
        max_calls = 10
        call_count = 0
        response = await llm_with_tools.ainvoke(messages)

        while hasattr(response, 'tool_calls') and response.tool_calls and call_count < max_calls:
            call_count += 1

            # 保存 AI 响应
            if response.content:
                messages.append(AIMessage(content=response.content))

            # 处理工具调用
            for tc in response.tool_calls:
                tc_name = tc.get('name') or (tc.get('function', {}).get('name') if isinstance(tc.get('function'), dict) else None)
                tc_args = tc.get('function', {}).get('arguments') if isinstance(tc.get('function'), dict) else tc.get('args', {})
                if isinstance(tc_args, str):
                    tc_args = json.loads(tc_args) if tc_args else {}
                tc_id = tc.get('id', '')

                if tc_name == 'get_chunk_context':
                    chunk_id = tc_args.get('chunk_id', '') if isinstance(tc_args, dict) else ''
                    tool_result = tool_handler.get_chunk_text(chunk_id)

                    # 添加工具结果
                    tool_msg = ToolMessage(
                        content=f"[已加载章节: {chunk_id}]\n\n{tool_result}",
                        tool_call_id=tc_id
                    )
                    messages.append(tool_msg)

            # 继续对话
            response = await llm_with_tools.invoke(messages)

        if not response.content:
            raise ValueError("LLM returned empty response")

        return response.content.strip()

    def _build_chapters_index(
        self,
        drafts: list["ChapterDraft"],
        chunks: dict[str, "Chunk"]
    ) -> str:
        """构建章节索引"""
        parts = []
        for i, draft in enumerate(drafts, 1):
            chunk = chunks.get(draft.chunk_id)
            title = chunk.chapter if chunk else draft.chunk_id
            word_count = len(draft.chapter_text)
            parts.append(f"- 第{i}章: {title} ({word_count}字)")
        return "\n".join(parts)

    def _build_chapters_text(self, drafts: list["ChapterDraft"]) -> str:
        """构建章节文本"""
        parts = []
        for i, draft in enumerate(drafts, 1):
            parts.append(f"【第{i}章】\n{draft.chapter_text}")
        return "\n\n---\n\n".join(parts)
