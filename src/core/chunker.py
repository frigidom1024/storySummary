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
    # Matches "Chapter N" (English) or "N、" (Chinese numeral) patterns
    CHAPTER_PATTERN = re.compile(
        r'^Chapter\s+(\d+|M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))\s*$|^[一二三四五六七八九十百千]+、',
        re.MULTILINE | re.IGNORECASE
    )

    # Standalone title pattern - short text without "Chapter" or Chinese numeral suffix
    TITLE_PATTERN = re.compile(r'^.{1,20}$')

    # Minimum content length to be considered valid chapter content
    MIN_CHUNK_LENGTH = 10

    def chunk(self, text: str) -> list[Chunk]:
        lines = text.split("\n")
        chunks = []
        current_chapter = None
        current_content = []
        order = 0
        is_first_line = True

        for line in lines:
            match = self.CHAPTER_PATTERN.match(line.strip())
            if match:
                # Found a chapter heading
                if current_content:
                    # Save previous chapter's content if it has enough length
                    chunk_text = "\n\n".join(current_content)
                    if len(chunk_text) >= self.MIN_CHUNK_LENGTH:
                        chunks.append(Chunk(
                            id=f"chunk-{order:04d}",
                            text=chunk_text,
                            chapter=current_chapter,
                            order=order
                        ))
                        order += 1
                    current_content = []
                current_chapter = line.strip()
                is_first_line = False
            else:
                if line.strip():
                    # Skip short first lines that look like titles
                    if is_first_line and len(line.strip()) < 20:
                        # Attach title to first chapter as prefix
                        if current_chapter is None:
                            current_chapter = line.strip()
                        else:
                            current_content.append(line)
                    else:
                        current_content.append(line)
                    is_first_line = False

        # Don't forget the last chapter
        if current_content:
            chunk_text = "\n\n".join(current_content)
            if len(chunk_text) >= self.MIN_CHUNK_LENGTH:
                chunks.append(Chunk(
                    id=f"chunk-{order:04d}",
                    text=chunk_text,
                    chapter=current_chapter,
                    order=order
                ))

        return chunks