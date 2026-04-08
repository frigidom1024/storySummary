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
    # Matches "Chapter N" where N is Arabic numerals or Roman numerals (I, II, III, IV, V, VI, VII, VIII, IX, X, etc.)
    CHAPTER_PATTERN = re.compile(
        r'^Chapter\s+(\d+|M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))\s*$',
        re.MULTILINE | re.IGNORECASE
    )

    def chunk(self, text: str) -> list[Chunk]:
        lines = text.split("\n")
        chunks = []
        current_chapter = None
        current_content = []
        order = 0

        for line in lines:
            match = self.CHAPTER_PATTERN.match(line.strip())
            if match:
                if current_content:
                    chunks.append(Chunk(
                        id=f"chunk-{order:04d}",
                        text="\n\n".join(current_content),
                        chapter=current_chapter,
                        order=order
                    ))
                    order += 1
                    current_content = []
                current_chapter = line.strip()
            else:
                if line.strip():
                    current_content.append(line)

        if current_content:
            chunks.append(Chunk(
                id=f"chunk-{order:04d}",
                text="\n\n".join(current_content),
                chapter=current_chapter,
                order=order
            ))

        return chunks