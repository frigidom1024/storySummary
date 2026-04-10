import re
from typing import Iterator
from src.models.chunk import Chunk


class TextChunker:
    def __init__(self, chunk_size: int = 1):
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        for i in range(0, len(paragraphs), self.chunk_size):
            group = paragraphs[i:i + self.chunk_size]
            chunk_text = "\n\n".join(group)
            chunks.append(Chunk(
                id=f"chunk-{len(chunks):04d}",
                text=chunk_text,
                order=len(chunks)
            ))
        return chunks


class ChapterChunker:
    """
    Splits novel text into chapter-based chunks.

    Handles formats like:
      - "第一部 Ⅰ 今天妈妈死了" (inline: section + Roman numeral)
      - "第一章 标题" (standalone Chinese chapter)
      - "Chapter 1" (English)
    """

    # Chinese section markers: 第X部, 第X篇
    SECTION_PATTERN = re.compile(r'第([0-9零一二三四五六七八九十百千万]+)[部篇]')

    # Chinese chapter markers: 第X章, 第X节
    CHAPTER_PATTERN = re.compile(
        r'第[0-9零一二三四五六七八九十百千万\d]+[章节]'
    )

    # Standalone Chinese numeral chapter: "一、", "二、", "三、" (at start of line)
    CHINESE_NUM_CHAPTER_PATTERN = re.compile(r'^([零一二三四五六七八九十百千万]+)、\s*(.*)$', re.MULTILINE)

    # Standalone Chinese numeral with parentheses: "(一)", "(二)", etc.
    PAREN_CHINESE_NUM_PATTERN = re.compile(r'^\（([零一二三四五六七八九十百千万]+)）\s*(.*)$', re.MULTILINE)

    # Roman numeral chapter markers (must be preceded by non-Roman)
    ROMAN_PATTERN = re.compile(
        r'(?<=[^ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ])'
        r'([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ])\s+'
    )

    # Appendix markers: 附 录, 附录
    APPENDIX_PATTERN = re.compile(r'附\s*录')

    # English Chapter pattern - matches "Chapter 1", "Chapter I", "Chapter IV", etc.
    ENGLISH_CHAPTER_PATTERN = re.compile(
        r'^Chapter\s+([IVX0-9]+)',
        re.IGNORECASE | re.MULTILINE
    )

    # Minimum content length for a chunk
    MIN_CHUNK_LENGTH = 10

    def _has_any_marker(self, text: str) -> bool:
        """Check if text contains any chapter/section marker."""
        return bool(
            self.SECTION_PATTERN.search(text) or
            self.ROMAN_PATTERN.search(text) or
            self.CHAPTER_PATTERN.match(text) or
            self.ENGLISH_CHAPTER_PATTERN.match(text) or
            self.APPENDIX_PATTERN.search(text)
        )

    def chunk(self, text: str) -> list[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        order = 0

        current_section = None   # "第一部", "第二部", etc.
        current_chapter = None   # "Ⅰ", "第二章", etc.
        current_content = []
        chars_since_last_marker = 0  # Track content length since last chapter marker

        def has_real_content(text: str) -> bool:
            """Check if text has enough prose characters to be real content."""
            if not text or len(text.strip()) < 5:
                return False
            chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
            # Chinese text needs Chinese chars, other text needs basic length
            if chinese > 0:
                return chinese >= 8
            return len(text.strip()) >= 10

        def finalize_chunk():
            """Save accumulated content as a chunk."""
            nonlocal order, current_content, current_chapter, chars_since_last_marker
            if current_content:
                chunk_text = "\n\n".join(current_content)
                if len(chunk_text) >= self.MIN_CHUNK_LENGTH:
                    label = current_chapter or current_section
                    chunks.append(Chunk(
                        id=f"chunk-{order:04d}",
                        text=chunk_text,
                        chapter=label,
                        order=order
                    ))
                    order += 1
                current_content = []
                chars_since_last_marker = 0

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]

            # Detect section marker (第一部, 第二部, etc.) near paragraph start
            section_match = self.SECTION_PATTERN.search(para)
            # Detect inline Roman numeral marker
            roman_match = self.ROMAN_PATTERN.search(para)
            # Detect standalone chapter line
            chapter_match = self.CHAPTER_PATTERN.match(para)
            # Detect English chapter
            english_match = self.ENGLISH_CHAPTER_PATTERN.match(para)
            # Detect appendix
            appendix_match = self.APPENDIX_PATTERN.search(para)

            # Handle appendix marker
            if appendix_match and appendix_match.start() < 30:
                finalize_chunk()
                current_chapter = "附录"
                current_content.append(para[appendix_match.end():].strip() or para)
                i += 1
                continue

            # Handle section marker
            if section_match and section_match.start() < 30:
                finalize_chunk()
                current_section = section_match.group(0)  # e.g., "第一部"
                current_chapter = None
                after = para[section_match.end():].strip()
                if after and has_real_content(after):
                    current_content.append(after)
                    chars_since_last_marker = len(after)
                else:
                    chars_since_last_marker = 0
                i += 1
                continue

            # Handle Roman numeral chapter marker
            if roman_match and roman_match.start() < 30:
                after = para[roman_match.end():].strip()
                if has_real_content(after) or (len(after) > 3):
                    finalize_chunk()
                    if current_section:
                        current_chapter = f"{current_section} {roman_match.group(1)}"
                    else:
                        current_chapter = roman_match.group(1)
                    current_content.append(after)
                    chars_since_last_marker = len(after)
                    i += 1
                    continue
                elif after:
                    # Short content after marker - accumulate and check next para
                    current_content.append(para)
                    chars_since_last_marker += len(after)
                    i += 1
                    continue

            # Handle standalone chapter line
            if chapter_match:
                after = para[chapter_match.end():].strip()
                finalize_chunk()
                current_chapter = chapter_match.group(0)
                if has_real_content(after):
                    current_content.append(after)
                    chars_since_last_marker = len(after)
                else:
                    chars_since_last_marker = 0
                i += 1
                continue

            # Handle Chinese numeral chapter: "一、旧书店" or "二、约定"
            chinese_num_match = self.CHINESE_NUM_CHAPTER_PATTERN.match(para)
            if chinese_num_match:
                finalize_chunk()
                current_chapter = f"第{chinese_num_match.group(1)}章"
                after = chinese_num_match.group(2).strip()
                if has_real_content(after):
                    current_content.append(after)
                    chars_since_last_marker = len(after)
                else:
                    chars_since_last_marker = 0
                i += 1
                continue

            # Handle parenthesized Chinese numeral: "(一)", "(二)"
            paren_match = self.PAREN_CHINESE_NUM_PATTERN.match(para)
            if paren_match:
                finalize_chunk()
                current_chapter = f"第{paren_match.group(1)}章"
                after = paren_match.group(2).strip()
                if has_real_content(after):
                    current_content.append(after)
                    chars_since_last_marker = len(after)
                else:
                    chars_since_last_marker = 0
                i += 1
                continue

            # Handle English chapter
            if english_match:
                finalize_chunk()
                current_chapter = f"Chapter {english_match.group(1)}"
                after = para[english_match.end():].strip()
                if not after:
                    current_content.append(para)
                    chars_since_last_marker = len(para)
                else:
                    chars_since_last_marker = 0
                # Look ahead for content in following paragraphs
                i += 1
                while i < len(paragraphs) and not self._has_any_marker(paragraphs[i]):
                    current_content.append(paragraphs[i])
                    chars_since_last_marker += len(paragraphs[i])
                    i += 1
                continue

            # No chapter marker - accumulate content
            current_content.append(para)
            chars_since_last_marker += len(para)

            # Auto-split if accumulated content is large with no chapter marker
            if chars_since_last_marker > 40000 and current_chapter:
                finalize_chunk()

            i += 1

        finalize_chunk()
        return chunks
