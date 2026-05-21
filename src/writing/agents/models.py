"""生成流程相关的数据模型定义"""

from pydantic import BaseModel, Field
from typing import Optional


# ====================== 统一草稿模型 ======================

class Draft(BaseModel):
    """统一的草稿模型（Intro/Chapter/Reflection 共用）"""
    section_id: str = Field(default="", description="部分ID（如 'intro', 'chapter-1', 'reflection'）")
    draft_type: str = Field(description="草稿类型: intro/chapter/reflection")
    content: str = Field(default="", description="草稿正文")


class DraftSection(BaseModel):
    """大纲中的单个章节/部分，对应一个草稿"""
    section_id: str = Field(description="部分ID（与 draft.section_id 对应）")
    section: str = Field(description="章节/段落名称")
    type: str = Field(description="类型: author_intro/story_content/reflection")
    chapter: Optional[int] = Field(default=None, description="章节编号（story_content 时使用）")
    description: Optional[str] = Field(default=None, description="章节描述")


# ====================== Outline Agent ======================

class ManuscriptOutline(BaseModel):
    """口播稿大纲完整结构"""
    manuscript_outline: list[DraftSection] = Field(description="章节结构列表")
    metadata: dict = Field(default_factory=dict, description="元数据（如 tone）")


class OutlineResult(BaseModel):
    """OutlineAgent 的输出结果"""
    story_synopsis: str = Field(description="故事梗概（自然语言）")
    manuscript_outline: ManuscriptOutline = Field(description="口播稿大纲结构")
    chapter_summaries: str = Field(description="章节摘要（用于参考）")


# ====================== Style Learning Agent ======================

class StyleProfile(BaseModel):
    """分类型的风格画像"""
    structure_style: str = ""  # 整体结构风格 - 用于 outline 参考
    narrative_style: str = ""  # 正文叙述风格 - 用于 writer 参考
    intro_style: str = ""  # 开篇介绍风格 - 用于 guide.write_intro
    reflection_style: str = ""  # 总结思考风格 - 用于 guide.write_reflection


# ====================== Writer Agents ======================

class ChapterWriterInput(BaseModel):
    """ChapterWriter 的输入参数"""
    chunk_id: str
    chapter_title: str
    nodes_text: str
    chunk_text: str
    last_draft_tail: str = ""  # 前一章结尾（用于衔接）
    outline_context: str = ""  # 前后章节结构信息
    narrative_style: Optional[str] = None  # 叙述风格参考


class ChapterWriterOutput(BaseModel):
    """ChapterWriter 的输出"""
    chapter_text: str = Field(description="生成的口播稿章节正文")
    section_id: str = Field(description="对应的 section_id（如 'chapter-1'）")


class GuideIntroInput(BaseModel):
    """GuideAgent 开篇介绍的输入"""
    book_id: str
    chunk: dict  # 包含 chapter 和 text 的 chunk 信息
    intro_style: Optional[str] = None


class GuideIntroOutput(BaseModel):
    """GuideAgent 开篇介绍的输出"""
    intro_text: str = Field(description="生成的开篇介绍")


class GuideReflectionInput(BaseModel):
    """GuideAgent 总结思考的输入"""
    book_id: str
    chunk: dict  # 包含 chapter 和 text 的 chunk 信息
    full_manuscript: str  # 完整口播稿（用于参考）
    reflection_style: Optional[str] = None


class GuideReflectionOutput(BaseModel):
    """GuideAgent 总结思考的输出"""
    reflection_text: str = Field(description="生成的总结思考")


# ====================== Polish Agent ======================

class PolishInput(BaseModel):
    """PolishAgent 的输入"""
    draft_text: str = Field(description="待润色的草稿全文")
    chapter_count: int = Field(description="章节数量")


class PolishOutput(BaseModel):
    """PolishAgent 的输出"""
    polished_text: str = Field(description="润色后的全文")


# ====================== Pipeline Results ======================

class ManuscriptResult(BaseModel):
    """完整的口播稿生成结果"""
    title: str = Field(description="书名")
    book_id: str = Field(description="书籍ID")
    drafts: list[Draft] = Field(default_factory=list, description="所有草稿")
    style_profile: Optional[StyleProfile] = Field(default=None, description="风格画像")
    outline: Optional[ManuscriptOutline] = Field(default=None, description="口播稿大纲")
    synopsis: str = Field(default="", description="故事梗概")
    final_manuscript: Optional[str] = Field(default=None, description="最终口播稿")
    phase: str = Field(default="", description="当前阶段: writing/polishing/done")

    def get_draft(self, section_id: str) -> Optional[Draft]:
        """根据 section_id 获取草稿"""
        for draft in self.drafts:
            if draft.section_id == section_id:
                return draft
        return None

    def get_drafts_by_type(self, draft_type: str) -> list[Draft]:
        """根据类型筛选草稿"""
        return [d for d in self.drafts if d.draft_type == draft_type]