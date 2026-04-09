"""
EPUB file reader utility.
Converts EPUB files to plain text for pipeline processing.
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import re


class EpubReader:
    """Read EPUB files and extract text content."""

    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        self.metadata: dict = {}
        self.chapters: list[dict] = []  # [{"title": str, "content": str, "order": int}]
        self._opf_dir: str = ""

    def read(self) -> str:
        """Read EPUB and return full text content."""
        self._extract_metadata()
        self._extract_content()

        # Build full text with chapter titles
        full_text = self._build_text()
        return full_text

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
        """Extract text content from each chapter."""
        with zipfile.ZipFile(self.epub_path, "r") as zf:
            opf_path = self._find_opf(zf)
            if not opf_path:
                return

            opf_content = zf.read(opf_path).decode("utf-8")

            # Build manifest: id -> href (using regex for flexibility)
            manifest = {}
            # Pattern handles attributes in any order
            for match in re.finditer(r'<item\s+([^>]+)/>', opf_content):
                attrs = match.group(1)
                id_match = re.search(r'id=["\']([^"\']+)["\']', attrs)
                href_match = re.search(r'href=["\']([^"\']+)["\']', attrs)
                if id_match and href_match:
                    manifest[id_match.group(1)] = href_match.group(1)

            # Get spine order
            spine_ids = re.findall(r'<itemref[^>]+idref=["\']([^"\']+)["\'][^>]*/>', opf_content)

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
                        self.chapters.append({
                            "title": title or f"Chapter {order + 1}",
                            "content": text,
                            "order": order
                        })
                        order += 1
                except KeyError:
                    continue

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from content using regex-based approach."""
        # Remove script and style elements first
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Handle CDATA sections
        html = re.sub(r'<!\[CDATA\[.*?\]\]>', '', html, flags=re.DOTALL)

        # Replace common HTML entities
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&amp;', '&')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&quot;', '"')
        html = html.replace('&#39;', "'")
        html = html.replace('&apos;', "'")

        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', html)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()


    def _extract_title(self, html: str) -> Optional[str]:
        """Try to extract title from HTML content."""
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

    def _build_text(self) -> str:
        """Build full text with chapter markers."""
        parts = []

        # Add metadata as header
        if self.metadata.get("title"):
            parts.append(f"# {self.metadata['title']}\n")
        if self.metadata.get("creator"):
            parts.append(f"作者: {self.metadata['creator']}\n")

        parts.append("\n")

        # Add chapters
        for chapter in self.chapters:
            parts.append(f"\n## {chapter['title']}\n\n")
            parts.append(chapter["content"])
            parts.append("\n\n")

        return "".join(parts)

    @property
    def title(self) -> str:
        return self.metadata.get("title", self.epub_path.stem)

    @property
    def author(self) -> str:
        return self.metadata.get("creator", "Unknown")


def read_epub(epub_path: str) -> str:
    """Convenience function to read EPUB file."""
    reader = EpubReader(epub_path)
    return reader.read()


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Convert EPUB to text")
    parser.add_argument("epub", help="Path to EPUB file")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    parser.add_argument("--title", action="store_true", help="Print metadata only")

    args = parser.parse_args()

    reader = EpubReader(args.epub)

    if args.title:
        print(f"Title: {reader.title}")
        print(f"Author: {reader.author}")
        print(f"Chapters: {len(reader.chapters)}")
    else:
        text = reader.read()
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Saved to {args.output}")
        else:
            print(text)
