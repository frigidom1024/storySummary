import os
import json
from typing import List, Dict, Any, TYPE_CHECKING
from langchain_core.tools import tool
from langchain.agents import create_agent
from src.core.node_generator import create_llm
from src.logging_config import debug

if TYPE_CHECKING:
    from src.models.chunk import Chunk
    from src.generation.models import ChapterDraft

# ====================== 系统提示词（保持你原来的，我稍微强化了Agent能力）======================
POLISH_SYSTEM_PROMPT = """
你是一个专业播客稿编辑，负责对多章节小说解说稿进行逐章高质量润色。

润色规则：
1. 消除重复内容
2. 统一口语化语气
3. 强化章节过渡自然
4. 结尾升华主题
5. 加入主播个人思考，不要纯复述
6. 必须对照原文核实情节

你可以使用工具查看任意章节原文，确保润色准确。
请一步一步思考，先规划，再调用工具，最后输出完整润色稿。

输出格式必须严格遵守：
【第X章润色】
内容

【完整稿子】
全部合并内容
"""

# ====================== 工具：获取章节原文（Agent可直接调用）======================
def create_chunk_tool(chunks: Dict[str, "Chunk"]):
    @tool
    def get_chunk_context(chunk_id: str) -> str:
        """获取指定章节ID的原文内容，用于核对情节、事实准确性。
        每次只能加载一个章节，加载新章节会自动替换旧章节。
        """
        chunk = chunks.get(chunk_id)
        if not chunk:
            return f"未找到章节 {chunk_id}"
        title = chunk.chapter or f"章节{chunk.order+1}"
        return f"【{title}】\n{chunk.text}"
    
    return get_chunk_context

# ====================== 核心：ReAct Agent 润色器 ======================
class PolishAgent:
    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def polish(
        self,
        drafts: List["ChapterDraft"],
        chunks: Dict[str, "Chunk"],
    ) -> str:
        if self.debug_mode:
            debug("polish", "[POLISH] 开始润色: drafts={} chunks={}", len(drafts), len(chunks))

        # 1. 创建工具
        get_chunk_tool = create_chunk_tool(chunks)
        tools = [get_chunk_tool]

        # 2. 使用新的 create_agent API
        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=POLISH_SYSTEM_PROMPT,
        )

        # 3. 构建输入
        chapters_index = self._build_chapters_index(drafts, chunks)
        chapters_text = self._build_chapters_text(drafts)

        if self.debug_mode:
            debug("polish", "[POLISH] 章节索引:\n{}", chapters_index)
            debug("polish", "[POLISH] 待润色稿子总长度: {} 字", len(chapters_text))

        user_input = f"""请润色以下多章节播客稿：

## 章节索引
{chapters_index}

## 待润色稿子
{chapters_text}

请先通读全文 → 按需调用get_chunk_context核对原文 → 逐章润色 → 输出最终稿。"""

        # 4. 运行 Agent - 直接invoke让它自动处理tool calling
        inputs = {"messages": [{"role": "user", "content": user_input}]}

        if self.debug_mode:
            debug("polish", "[POLISH] 开始调用 agent...")

        # 直接调用，create_agent 会自动处理 tool calling 循环
        result = agent.invoke(inputs)
        messages = result.get("messages", [])

        if self.debug_mode:
            debug("polish", "[POLISH] agent 执行完成，messages 数量: {}", len(messages))

        # 从最后一条 AIMessage 获取输出
        output = ""
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'ai':
                output = msg.content
                break
            elif isinstance(msg, dict) and msg.get("type") == "ai":
                output = msg.get("content", "")
                break

        output = output.strip()

        if self.debug_mode:
            debug("polish", "[POLISH] 润色完成: {} 字", len(output))
            debug("polish", "[POLISH] 输出预览: {}...", output[:200].replace('\n', ' '))

        return output

    # ===================== 你原来的工具函数，完全不变 =====================
    def _build_chapters_index(self, drafts, chunks):
        parts = []
        for i, d in enumerate(drafts, 1):
            c = chunks.get(d.chunk_id)
            title = c.chapter if c and c.chapter else d.chunk_id
            parts.append(f"- 第{i}章：{title}")
        return "\n".join(parts)

    def _build_chapters_text(self, drafts):
        parts = []
        for i, d in enumerate(drafts, 1):
            parts.append(f"## 第{i}章\n{d.chapter_text}")
        return "\n\n".join(parts)