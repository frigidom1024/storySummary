import os

from langchain.agents import create_agent

from src.core.node_generator import create_llm
from src.logging_config import debug


class StyleLearningAgent:
    """从参考口播稿提炼可复用的抽象风格画像。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.2)

    async def learn(self, reference_script: str) -> str:
        script = (reference_script or "").strip()
        if not script:
            return ""

        system_prompt = """你是口播风格分析师。你的任务是把参考口播稿提炼成"可执行风格规范"，供写作 agent 使用。

要求：
- 只总结风格，不改写剧情，不新增剧情。
- 输出要抽象且可操作，避免空话。
- 覆盖：整体结构、开场方式、段落推进、信息密度、句式节奏、口头禅、语气、转场、收尾、禁忌表达。
- 给出"应做/不应做"的明确清单，便于后续章节写作遵循。"""

        user_prompt = f"""请分析以下参考口播稿，并输出风格画像：

1) 风格总览（3-5条）
2) 结构模板（开场/展开/转场/收束）
3) 语言与句式特征（短句比例、停顿习惯、常用表达、口头禅）
4) 叙事策略（如何讲细节、如何讲观点、如何处理伏笔）
5) 约束与禁忌（至少5条）
6) 可直接给写作 agent 的执行清单（10条以内）

参考口播稿：
```参考
{script}
```"""

        if self.debug_mode:
            debug("style", "[STYLE] script_length={}", len(script))

        agent = create_agent(
            model=self.llm,
            tools=[],
            system_prompt=system_prompt,
            debug=self.debug_mode,
            name="style-learning-agent",
        )
        response = await agent.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})
        output = self._extract_output(response)
        if not output:
            raise ValueError("StyleLearningAgent returned empty response")
        return output

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
