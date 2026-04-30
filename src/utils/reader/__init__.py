"""Reader 层：统一接口读取不同文件类型"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List
import json
import logging
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from src.models.chunk import Chunk
from src.config import config


def _create_default_llm() -> ChatOpenAI:
    """创建默认 LLM 实例。"""
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_API_BASE,
        model=config.OPENAI_MODEL,
        temperature=0.1,
    )


async def classify_content_types(
    chunks: List[Chunk],
    llm: Optional[BaseChatModel] = None,
) -> List[Chunk]:
    """用 LLM 批量分类章节内容类型，返回更新后的 chunks。

    Args:
        chunks: 待分类的章节列表
        llm: LangChain BaseChatModel 实例，不传则使用默认配置

    Returns:
        更新了 content_type 字段的 chunks 列表
    """
    if llm is None:
        llm = _create_default_llm()

    if not chunks:
        return chunks

    # 准备每个章节的标题+前200字
    chapter_briefs = []
    for i, ch in enumerate(chunks):
        preview = ch.text[:200] if ch.text else ""
        chapter_briefs.append(f'{i + 1}. [{ch.chapter or f"Chapter {i + 1}"}] {preview}')

    system_prompt = """You are a content classifier. Given a list of book chapters with their titles and opening text, classify each chapter's content type.

Classify each chapter as ONE of:
- story_content: narrative/story text (novel chapters, main body)
- appendix: back matter (afterword, chronology, appendix, awards, Nobel speech, author biography)
- author_intro: front matter or author introduction (preface, foreword, introduction, translator's note)
- other: anything that doesn't fit the above

Output JSON array only:
[{"index": 1, "content_type": "story_content"}, {"index": 2, "content_type": "appendix"}, ...]

Rules:
1. index starts from 1, matching chapter order
2. Only output one of the four types, no guessing
3. Nobel acceptance speeches, author chronologies, appendices belong to "appendix"
4. Author prefaces, translator prefaces belong to "author_intro"
5. Regular book chapters (any number/part) are "story_content"""

    logger = logging.getLogger(__name__)

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(chapter_briefs)}
        ])
        content = response.content if hasattr(response, "content") else str(response)
        logger.debug(f"Classification LLM response: {content[:500]}")

        # 提取 JSON
        json_start = content.find("[")
        json_end = content.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            parsed = json.loads(content[json_start:json_end])
            logger.debug(f"Parsed classification: {parsed}")
            index_to_type = {item["index"]: item["content_type"] for item in parsed}
            for i, ch in enumerate(chunks):
                ch.content_type = index_to_type.get(i + 1, "other")
        else:
            logger.warning(f"No JSON array found in LLM response: {content[:200]}")
            for ch in chunks:
                ch.content_type = "other"
    except Exception as e:
        logger.error(f"AI classification failed: {e}", exc_info=True)
        for ch in chunks:
            ch.content_type = "other"

    return chunks


class BookReader(ABC):
    """抽象基类，定义所有 Reader 的统一接口"""

    @property
    @abstractmethod
    def text(self) -> str:
        """完整文本内容（含元数据和章节标题）"""

    @property
    @abstractmethod
    def title(self) -> str:
        """书名"""

    @property
    @abstractmethod
    def author(self) -> str:
        """作者"""

    @property
    def chapters(self) -> list[Chunk]:
        """章节列表"""
        return []

    @property
    def metadata(self) -> dict:
        """完整元数据"""
        return getattr(self, '_metadata', {})

    @metadata.setter
    def metadata(self, value: dict):
        self._metadata = value


def read_book(book_path: str) -> BookReader:
    """自动检测文件类型，返回对应 Reader（数据已在 __init__ 中加载）"""
    path = Path(book_path)
    suffix = path.suffix.lower()

    if suffix == ".epub":
        from src.utils.reader.epub import EpubReader
        return EpubReader(book_path)
    elif suffix == ".pdf":
        from src.utils.reader.pdf import PdfReader
        return PdfReader(book_path)
    elif suffix == ".txt":
        from src.utils.reader.text import TxtReader
        return TxtReader(book_path)
    else:
        raise ValueError(
            f"Unsupported book format: {suffix}. Supported: .epub, .pdf, .txt"
        )
