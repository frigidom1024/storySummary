import os
import json
from typing import List, Dict, Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.messages import SystemMessage
from src.core.node_generator import create_llm

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
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def polish(
        self,
        drafts: List["ChapterDraft"],
        chunks: Dict[str, "Chunk"],
    ) -> str:
        # 1. 创建工具
        get_chunk_tool = create_chunk_tool(chunks)
        tools = [get_chunk_tool]

        # 2. 构建 ReAct 提示词
        prompt = ChatPromptTemplate.from_messages([
            ("system", POLISH_SYSTEM_PROMPT),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 3. 创建 Agent
        agent = create_react_agent(self.llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=12,
            verbose=True,
            handle_parsing_errors="continue"
        )

        # 4. 构建输入（和你原来一样）
        chapters_index = self._build_chapters_index(drafts, chunks)
        chapters_text = self._build_chapters_text(drafts)

        user_input = f"""
请润色以下多章节播客稿：

## 章节索引
{chapters_index}

## 待润色稿子
{chapters_text}

请先通读全文 → 按需调用get_chunk_context核对原文 → 逐章润色 → 输出最终稿。
"""

        # 5. 运行 Agent（自动思考、自动调用工具、自动循环）
        result = await executor.ainvoke({"input": user_input})
        return result["output"].strip()

    # ===================== 你原来的工具函数，完全不变 =====================
    def _build_chapters_index(self, drafts, chunks):
        parts = []
        for i, d in enumerate(drafts, 1):
            c = chunks.get(d.chunk_id)
            title = c.chapter if c else d.chunk_id
            parts.append(f"- 第{i}章：{title}")
        return "\n".join(parts)

    def _build_chapters_text(self, drafts):
        parts = []
        for i, d in enumerate(drafts, 1):
            parts.append(f"## 第{i}章\n{d.chapter_text}")
        return "\n\n".join(parts)