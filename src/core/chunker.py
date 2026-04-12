import re
from typing import Optional
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


class SmartChunker:
    """
    A通用智能分块器，支持多种文本格式和语言。

    Features:
    - 自动检测章节标记（中文、英文、日文等）
    - 支持多种编号系统（阿拉伯数字、中文数字、罗马数字）
    - 对于无章节标记的文本，按字符数自动分块
    - 可配置的最小/最大块大小
    """

    CHINESE_DIGITS = '零一二三四五六七八九十百千万'

    SECTION_MARKERS = [
        r'第[0-9零一二三四五六七八九十百千万\d]+[部篇卷册]',
    ]

    CHAPTER_MARKERS = [
        r'第[0-9零一二三四五六七八九十百千万\d]+[章节]',
        r'[0-9零一二三四五六七八九十百千万\d]+[章节]',
    ]

    NUMBERED_CHAPTER_PATTERNS = [
        r'^([0-9]+)[\.、\.\s].+$',
        r'^([A-Z])[\.\s].+$',
        r'^(\([0-9]+\))[\.\s]*',
        r'^(\([A-Z]+\))[\.\s]*',
    ]

    CHINESE_NUM_CHAPTER_PATTERNS = [
        r'^([零一二三四五六七八九十百千万]+)、\s*(.*)$',
        r'^\（([零一二三四五六七八九十百千万]+)）\s*(.*)$',
        r'^\[([零一二三四五六七八九十百千万]+)\]\s*(.*)$',
    ]

    ROMAN_NUMERALS = 'ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ'
    ENGLISH_CHAPTER_PATTERNS = [
        r'^Chapter\s+([IVX0-9]+)',
        r'^CHAPTER\s+([IVX0-9]+)',
        r'^Part\s+([IVX0-9]+)',
        r'^PART\s+([IVX0-9]+)',
        r'^Section\s+([0-9]+)',
        r'^SECTION\s+([0-9]+)',
    ]

    JAPANESE_CHAPTER_PATTERNS = [
        r'^第([0-9一二三四五六七八九十]+)[話篇]',
        r'^([0-9一二三四五六七八九十]+)話',
    ]

    SPECIAL_MARKERS = [
        r'附\s*录',
        r'后\s*记',
        r'序\s*言',
        r'尾\s*声',
        r'楔\s*子',
    ]

    MAX_CHUNK_CHARS = 30000
    MIN_CHUNK_CHARS = 500
    IDEAL_CHUNK_CHARS = 8000

    def __init__(
        self,
        max_chunk_chars: int = 30000,
        min_chunk_chars: int = 500,
        ideal_chunk_chars: int = 8000,
        auto_split_threshold: int = 15000,
    ):
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars
        self.ideal_chunk_chars = ideal_chunk_chars
        self.auto_split_threshold = auto_split_threshold
        self._compile_patterns()

    def _compile_patterns(self):
        self.section_patterns = [re.compile(p) for p in self.SECTION_MARKERS]
        self.chapter_patterns = [re.compile(p) for p in self.CHAPTER_MARKERS]
        self.numbered_chapter_patterns = [re.compile(p, re.MULTILINE) for p in self.NUMBERED_CHAPTER_PATTERNS]
        self.chinese_chapter_patterns = [re.compile(p, re.MULTILINE) for p in self.CHINESE_NUM_CHAPTER_PATTERNS]
        self.english_chapter_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.ENGLISH_CHAPTER_PATTERNS]
        self.japanese_chapter_patterns = [re.compile(p, re.MULTILINE) for p in self.JAPANESE_CHAPTER_PATTERNS]
        self.special_patterns = [re.compile(p) for p in self.SPECIAL_MARKERS]

    def _is_chapter_marker(self, text: str) -> Optional[tuple[str, str]]:
        text = text.strip()
        if not text:
            return None

        for pattern in self.section_patterns:
            m = pattern.match(text)
            if m:
                return ('section', m.group(0))

        for pattern in self.chapter_patterns:
            m = pattern.match(text)
            if m:
                return ('chapter', m.group(0))

        for pattern in self.chinese_chapter_patterns:
            m = pattern.match(text)
            if m:
                return ('chapter', f"第{m.group(1)}章")

        for pattern in self.english_chapter_patterns:
            m = pattern.match(text)
            if m:
                return ('chapter', m.group(0))

        for pattern in self.japanese_chapter_patterns:
            m = pattern.match(text)
            if m:
                return ('chapter', m.group(0))

        for pattern in self.numbered_chapter_patterns:
            m = pattern.match(text)
            if m:
                return ('chapter', m.group(1))

        for pattern in self.special_patterns:
            m = pattern.match(text)
            if m:
                return ('special', m.group(0))

        if self._looks_like_chapter_title(text):
            return ('chapter', text[:20])

        return None

    def _looks_like_chapter_title(self, text: str) -> bool:
        text = text.strip()
        if len(text) > 50 or len(text) < 2:
            return False

        if text.isdigit():
            return True

        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_count >= 2 and chinese_count / len(text) > 0.5:
            if not any(c in text for c in '，。、；：""''（）'):
                if text.startswith(('第', '【', '[')):
                    return True

        if re.match(r'^[A-Z\s\-]+$', text) and 2 < len(text) < 30:
            return True

        return False

    def _split_into_sentences(self, text: str) -> list[str]:
        sentence_endings = r'[。！？!?\.．;；]'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk(self, text: str) -> list[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            return [Chunk(id="chunk-0000", text=text.strip(), order=0)]

        marker_type = self._detect_overall_marker_type(paragraphs)

        if marker_type == 'none':
            return self._chunk_without_markers(paragraphs)

        return self._chunk_with_markers(paragraphs)

    def _detect_overall_marker_type(self, paragraphs: list[str]) -> str:
        has_chinese = False
        has_english = False
        has_roman = False
        chapter_like_count = 0

        for p in paragraphs[:min(20, len(paragraphs))]:
            if re.search(r'[\u4e00-\u9fff]', p):
                has_chinese = True
            if re.search(r'Chapter|CHAPTER|Part|PART|Section|SECTION', p):
                has_english = True
            if re.search(r'[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]', p):
                has_roman = True
            if self._is_chapter_marker(p):
                chapter_like_count += 1

        if chapter_like_count >= 3:
            return 'structured'

        if has_english and not has_chinese:
            return 'english'

        if has_chinese:
            return 'chinese'

        return 'numbered'

    def _chunk_without_markers(self, paragraphs: list[str]) -> list[Chunk]:
        chunks = []
        current_chunk = []
        current_size = 0
        order = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > self.max_chunk_chars and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_chars:
                    chunks.append(Chunk(
                        id=f"chunk-{order:04d}",
                        text=chunk_text,
                        chapter=f"片段 {order + 1}",
                        order=order
                    ))
                    order += 1
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_size

            if current_size >= self.ideal_chunk_chars and len(current_chunk) >= 2:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(Chunk(
                    id=f"chunk-{order:04d}",
                    text=chunk_text,
                    chapter=f"片段 {order + 1}",
                    order=order
                ))
                order += 1
                current_chunk = []
                current_size = 0

        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(Chunk(
                id=f"chunk-{order:04d}",
                text=chunk_text,
                chapter=f"片段 {order + 1}",
                order=order
            ))

        return chunks

    def _chunk_with_markers(self, paragraphs: list[str]) -> list[Chunk]:
        chunks = []
        order = 0

        current_section = None
        current_chapter = None
        current_content = []
        content_chars = 0

        def finalize():
            nonlocal order, current_content, current_chapter, content_chars
            if current_content:
                chunk_text = "\n\n".join(current_content)
                if len(chunk_text) >= self.min_chunk_chars:
                    label = current_chapter or current_section or f"章节 {order + 1}"
                    chunks.append(Chunk(
                        id=f"chunk-{order:04d}",
                        text=chunk_text,
                        chapter=label,
                        order=order
                    ))
                    order += 1
                current_content = []
                content_chars = 0

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            marker_result = self._is_chapter_marker(para)

            if marker_result:
                marker_type, marker_value = marker_result

                if marker_type == 'section':
                    finalize()
                    current_section = marker_value
                    current_chapter = None

                    rest = para[len(marker_value):].strip()
                    if rest:
                        current_content.append(rest)
                        content_chars += len(rest)

                elif marker_type == 'chapter':
                    finalize()
                    current_chapter = marker_value

                    rest = para[len(marker_value):].strip() if len(marker_value) < len(para) else ""
                    if rest and self._has_real_content(rest):
                        current_content.append(rest)
                        content_chars += len(rest)

                elif marker_type == 'special':
                    finalize()
                    current_chapter = marker_value

                i += 1
                continue

            current_content.append(para)
            content_chars += len(para)

            if content_chars >= self.max_chunk_chars:
                finalize()
                current_chapter = f"自动分段 {order + 1}"

            i += 1

        finalize()
        return chunks

    def _has_real_content(self, text: str) -> bool:
        if not text or len(text.strip()) < 5:
            return False

        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese > 0:
            return chinese >= 5

        alpha = len(re.findall(r'[a-zA-Z]', text))
        if alpha > 0:
            return alpha >= 10

        return len(text.strip()) >= 15


class AdaptiveChunker:
    """
    自适应分块器，根据文本特征自动选择最佳分块策略。
    """

    def __init__(
        self,
        max_chunk_chars: int = 30000,
        min_chunk_chars: int = 500,
        ideal_chunk_chars: int = 8000,
    ):
        self.smart_chunker = SmartChunker(
            max_chunk_chars=max_chunk_chars,
            min_chunk_chars=min_chunk_chars,
            ideal_chunk_chars=ideal_chunk_chars,
        )
        self.text_chunker = TextChunker(chunk_size=1)

    def chunk(self, text: str) -> list[Chunk]:
        sample = text[:2000]

        paragraph_count = text.count('\n\n') + 1
        avg_para_len = len(text) / max(paragraph_count, 1)

        if avg_para_len > 500:
            return self.smart_chunker.chunk(text)

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        has_many_short_lines = len([l for l in lines if len(l) < 100]) > len(lines) * 0.6

        if has_many_short_lines and avg_para_len < 100:
            return self.smart_chunker._chunk_without_markers(
                [p.strip() for p in text.split('\n\n') if p.strip()]
            )

        return self.smart_chunker.chunk(text)


class ChapterChunker:
    """
    Legacy wrapper for backward compatibility.
    Now delegates to AdaptiveChunker for better results.
    """

    MIN_CHUNK_LENGTH = 10

    def chunk(self, text: str) -> list[Chunk]:
        chunker = AdaptiveChunker(
            max_chunk_chars=30000,
            min_chunk_chars=self.MIN_CHUNK_LENGTH,
            ideal_chunk_chars=8000,
        )
        return chunker.chunk(text)