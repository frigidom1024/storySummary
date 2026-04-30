"""
EPUB file reader utility.
Converts EPUB files to plain text for pipeline processing.
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import re
import json

from src.utils.reader import BookReader
from src.models.chunk import Chunk

class EpubReader(BookReader):
    """Read EPUB files and extract text content."""

    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        self._metadata: dict = {}
        self._chapters: list[Chunk] = []
        self._opf_dir: str = ""
        self._text: str = ""

        # Load data immediately (except AI classification)
        self._extract_metadata()
        self._extract_content()
        self._filter_invalid_chapters()
        self._build_text()

    def _filter_invalid_chapters(self):
        """过滤无效章节（标题为"未知"、Cover、Contents 等）。"""
        invalid_patterns = ["未知", "Cover", "作家榜经典文库", "Contents", "目录"]
        min_content_len = 50  # 内容少于50字符视为无效

        self._chapters = [
            ch for ch in self._chapters
            if ch.chapter not in invalid_patterns
            and len(ch.text.strip()) >= min_content_len
        ]

        # 重新编号
        for i, ch in enumerate(self._chapters):
            ch.id = f"ch_{i}"
            ch.order = i

    def _extract_metadata(self):
        """Extract book metadata from OPF file."""
        with zipfile.ZipFile(self.epub_path, "r") as zf:
            opf_path = self._find_opf(zf)
            if not opf_path:
                return

            self._opf_dir = str(Path(opf_path).parent)
            opf_content = zf.read(opf_path).decode("utf-8")
            root = ET.fromstring(opf_content)

            # Extract metadata - handle both namespaced and non-namespaced
            for elem in root.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag in ("title", "creator", "language", "publisher"):
                    if elem.text:
                        self.metadata[tag] = elem.text.strip()
                elif tag == "identifier" and "identifier" not in self.metadata:
                    if elem.text:
                        self.metadata["identifier"] = elem.text.strip()

    def _find_opf(self, zf: zipfile.ZipFile) -> Optional[str]:
        """Find the OPF file path from container.xml."""
        try:
            container = zf.read("META-INF/container.xml").decode("utf-8")
            root = ET.fromstring(container)
            # Try both namespaced and non-namespaced
            for rootfile in root.iter():
                tag = rootfile.tag.split("}")[-1] if "}" in rootfile.tag else rootfile.tag
                if tag == "rootfile":
                    return rootfile.get("full-path")
        except KeyError:
            pass
        return None

    def _extract_content(self):
        """Extract text content from each chapter using XML parsing."""
        with zipfile.ZipFile(self.epub_path, "r") as zf:
            opf_path = self._find_opf(zf)
            if not opf_path:
                return

            opf_content = zf.read(opf_path).decode("utf-8")
            root = ET.fromstring(opf_content)

            # Build manifest: id -> href using XML parsing
            manifest = {}
            for item in root.iter():
                tag = item.tag.split("}")[-1] if "}" in item.tag else item.tag
                if tag == "item":
                    item_id = item.get("id")
                    href = item.get("href")
                    if item_id and href:
                        manifest[item_id] = href

            # Get spine order using XML parsing
            spine_ids = []
            for itemref in root.iter():
                tag = itemref.tag.split("}")[-1] if "}" in itemref.tag else itemref.tag
                if tag == "itemref":
                    idref = itemref.get("idref")
                    if idref:
                        spine_ids.append(idref)

            order = 0
            for idref in spine_ids:
                if idref not in manifest:
                    continue

                href = manifest[idref]
                # Resolve path relative to OPF location
                if self._opf_dir != ".":
                    href = f"{self._opf_dir}/{href}"
                href = href.lstrip("/")

                try:
                    content = zf.read(href).decode("utf-8")
                    text = self._strip_html(content)
                    title = self._extract_title(content)

                    if text.strip():
                        chunk = Chunk(
                            id=f"ch_{order}",
                            text=text,
                            chapter=title or f"Chapter {order + 1}",
                            order=order,
                            content_type="other",
                        )
                        self._chapters.append(chunk)
                        order += 1
                except KeyError:
                    continue
                except UnicodeDecodeError:
                    # Try with different encodings
                    try:
                        content = zf.read(href).decode("latin-1")
                        text = self._strip_html(content)
                        title = self._extract_title(content)

                        if text.strip():
                            chunk = Chunk(
                                id=f"ch_{order}",
                                text=text,
                                chapter=title or f"Chapter {order + 1}",
                                order=order,
                                content_type="other",
                            )
                            self._chapters.append(chunk)
                            order += 1
                    except Exception:
                        continue

    def _decode_numeric_entity(self, m):
        """Decode numeric HTML entity."""
        try:
            return chr(int(m.group(1)))
        except Exception:
            return m.group(0)

    def _decode_hex_entity(self, m):
        """Decode hex HTML entity."""
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from content using a more reliable approach."""
        try:
            # First, try to parse with XML
            root = ET.fromstring(f"<div>{html}</div>")
            text = ' '.join(root.itertext()).strip()
        except Exception:
            # Fallback to regex if XML parsing fails
            # Remove script and style elements first
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

            # Handle CDATA sections
            html = re.sub(r'<!\[CDATA\[.*?\]\]>', '', html, flags=re.DOTALL)

            # Replace common HTML entities (including numeric XML entities)
            html = re.sub(r'&#(\d+);', self._decode_numeric_entity, html)
            html = re.sub(r'&#x([0-9a-fA-F]+);', self._decode_hex_entity, html)
            html = html.replace('&nbsp;', ' ')
            html = html.replace('&amp;', '&')
            html = html.replace('&lt;', '<')
            html = html.replace('&gt;', '>')
            html = html.replace('&quot;', '"')
            html = html.replace('&#39;', "'")
            html = html.replace('&apos;', "'")

            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', '', html)

        # Replace non-breaking spaces and clean up whitespace
        text = text.replace('\xa0', ' ')
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _extract_title(self, html: str) -> Optional[str]:
        """Try to extract title from HTML content using XML parsing."""
        try:
            # Parse HTML with XML
            root = ET.fromstring(f"<div>{html}</div>")

            # Check title tag first
            for title_elem in root.iter():
                tag = title_elem.tag.split("}")[-1] if "}" in title_elem.tag else title_elem.tag
                if tag == "title":
                    if title_elem.text:
                        title = title_elem.text.strip()
                        if title:
                            return title

            # Check h1 tags
            for h1_elem in root.iter():
                tag = h1_elem.tag.split("}")[-1] if "}" in h1_elem.tag else h1_elem.tag
                if tag == "h1":
                    if h1_elem.text:
                        title = h1_elem.text.strip()
                        if title:
                            return title

            # Check h2 tags as fallback
            for h2_elem in root.iter():
                tag = h2_elem.tag.split("}")[-1] if "}" in h2_elem.tag else h2_elem.tag
                if tag == "h2":
                    if h2_elem.text:
                        title = h2_elem.text.strip()
                        if title:
                            return title
        except Exception:
            # Fallback to regex if XML parsing fails
            # Check title tag
            match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if title:
                    return title

            # Check first h1
            match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
            if match:
                title = self._strip_html(match.group(1)).strip()
                if title:
                    return title

        return None

    def _build_text(self):
        """Build full text with chapter markers, store in self._text."""
        parts = []

        # Add metadata as header
        if self.metadata.get("title"):
            parts.append(f"# {self.metadata['title']}\n")
        if self.metadata.get("creator"):
            parts.append(f"作者: {self.metadata['creator']}\n")

        parts.append("\n")

        # Add chapters
        for chunk in self._chapters:
            parts.append(f"\n## {chunk.chapter}\n\n")
            parts.append(chunk.text)
            parts.append("\n\n")

        self._text = "".join(parts)

    @property
    def text(self) -> str:
        """Return full text content."""
        return self._text

    @property
    def read(self) -> str:
        """Backward compatibility: return full text content."""
        return self._text

    @property
    def title(self) -> str:
        return self.metadata.get("title", self.epub_path.stem)

    @property
    def author(self) -> str:
        return self.metadata.get("creator", "Unknown")

    @property
    def chapters(self) -> list[Chunk]:
        return self._chapters
