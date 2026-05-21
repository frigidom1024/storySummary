import os
from typing import Optional

from langchain.agents import create_agent
from pydantic import BaseModel

from src.analysis.node_generator import create_llm
from src.logging_config import debug


class StyleProfile(BaseModel):
    """分类型的风格画像"""
    structure_style: str = ""  # 整体结构风格 - 用于 outline 参考
    narrative_style: str = ""  # 原文叙述风格 - 用于 writer 参考
    intro_style: str = ""  # 开篇介绍风格 - 用于 guide.write_intro
    reflection_style: str = ""  # 总结思考风格 - 用于 guide.write_reflection


class StyleLearningAgent:
    """从参考口播稿提炼可复用的抽象风格画像。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.2)

    async def learn(self, reference_script: str) -> str:
        """保持向后兼容：返回完整风格画像字符串"""
        profile = await self.learn_profile(reference_script)
        return self._profile_to_string(profile)

    async def learn_profile(self, reference_script: str) -> StyleProfile:
        """提取分类型的风格画像"""
        script = (reference_script or "").strip()
        if not script:
            return StyleProfile()

        system_prompt = """你是口播风格分析师。你的任务是把参考口播稿提炼成分类型的"抽象风格规范"。

## 核心原则
- 只提取写作方法论和风格规律，不引用原文内容
- 不要列举具体例子（人名/地名/台词/开场白原文）
- 输出要抽象可执行，避免空话套话
- 用 JSON 格式输出，包含四个字段

## JSON 格式
```json
{
  "structure_style": "整体结构风格（抽象描述）",
  "narrative_style": "正文叙述风格（抽象描述）",
  "intro_style": "开篇介绍风格（抽象描述）",
  "reflection_style": "总结思考风格（抽象描述）"
}
```

## 1. structure_style（整体结构风格）
用于 outline 构建参考。描述：
- 开场策略：用什么类型的信息/角度开头
- 结构特点：整体是线性/平行/螺旋？章节如何衔接
- 收尾方式：总结式/开放式/升华式？
- 节奏分布：各部分的大致比例和轻重

## 2. narrative_style（正文叙述风格）
用于 writer 写作故事内容。描述：
- 句式偏好：短句为主/长句为主/长短交替？
- 口语化程度：高度口语/适度书面/偏正式？
- 叙事人称：第一人称主导/第三人称/混合？
- 信息密度：密集型/舒缓型/张弛有度？
- 细节处理方式：重场景/重对话/重心理？

## 3. intro_style（开篇介绍风格）
用于 guide.write_intro。描述：
- 开场方式：从问候/故事/问题/感慨哪一种切入？
- 语气特征：亲切随和/沉稳厚重/轻松调侃？
- 信息推进：快速切入主题/渐进铺垫/悬念引入？
- 互动策略：提问互动/直接陈述/情感共鸣？

## 4. reflection_style（总结思考风格）
用于 guide.write_reflection。描述：
- 收尾策略：总结归纳/情感升华/开放式留白？
- 情感走向：感慨/启发/呼吁/平静？
- 思考深度：表面归纳/深层反思/哲学延伸？
- 结尾方式：回答开头/提出新问/戛然而止？

## 应做/不应做清单
最后给出5-8条"应做/不应做"清单。

直接输出 JSON，不要有其他内容。"""

        user_prompt = f"""请分析以下参考口播稿，输出三种分类型的风格画像。

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
        return self._parse_profile_response(response)

    async def learn_structure_style(self, reference_script: str) -> str:
        """仅提取整体结构风格（用于 outline 参考）"""
        profile = await self.learn_profile(reference_script)
        return profile.structure_style

    async def learn_narrative_style(self, reference_script: str) -> str:
        """仅提取原文叙述风格（用于 writer 参考）"""
        profile = await self.learn_profile(reference_script)
        return profile.narrative_style

    def _parse_profile_response(self, response) -> StyleProfile:
        """从 LLM 响应解析出分类型的风格画像"""
        text = self._extract_output(response)
        if not text:
            return StyleProfile()

        import json
        import re

        # 查找 JSON 对象
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return StyleProfile(
                    structure_style=self._flatten_field(data.get("structure_style", "")),
                    narrative_style=self._flatten_field(data.get("narrative_style", "")),
                    intro_style=self._flatten_field(data.get("intro_style", "")),
                    reflection_style=self._flatten_field(data.get("reflection_style", "")),
                )
            except json.JSONDecodeError:
                pass

        # 如果不是 JSON，尝试按段落分割
        sections = text.split("\n\n")
        if len(sections) >= 3:
            return StyleProfile(
                structure_style=sections[0].strip(),
                narrative_style=sections[1].strip(),
                intro_style=sections[2].strip() if len(sections) > 2 else "",
                reflection_style="\n\n".join(sections[3:]).strip() if len(sections) > 3 else "",
            )

        # fallback：整个文本作为 narrative_style
        return StyleProfile(narrative_style=text)

    def _flatten_field(self, value) -> str:
        """将字段值转换为字符串（处理嵌套 JSON 对象）"""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                if isinstance(v, str):
                    parts.append(f"{k}：{v}")
                elif isinstance(v, list):
                    parts.append(f"{k}：{'；'.join(str(i) for i in v)}")
                else:
                    parts.append(f"{k}：{v}")
            return "；".join(parts)
        if isinstance(value, list):
            return "；".join(str(i) for i in value)
        return str(value)

    def _profile_to_string(self, profile: StyleProfile) -> str:
        """将 StyleProfile 转换为字符串格式（保持向后兼容）"""
        parts = []
        if profile.structure_style:
            parts.append(f"## 整体结构风格\n{profile.structure_style}")
        if profile.narrative_style:
            parts.append(f"## 正文叙述风格\n{profile.narrative_style}")
        if profile.intro_style:
            parts.append(f"## 开篇介绍风格\n{profile.intro_style}")
        if profile.reflection_style:
            parts.append(f"## 总结思考风格\n{profile.reflection_style}")
        return "\n\n".join(parts)

    def _extract_output(self, response) -> str:
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