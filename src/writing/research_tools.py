from __future__ import annotations

from langchain_core.tools import tool

from src.models.chunk import Chunk
from src.storage.book_repository import BookRepository
from src.storage.vector_store import VectorStore


class ManuscriptResearchToolkit:
    """为写作 Agent 提供原文查找与向量检索工具。"""

    @staticmethod
    def create_tools(
        book_id: str,
        vector_path: str = "data/vectors",
    ):
        book_repository = BookRepository()
        vector_store = VectorStore(vector_path)

        @tool
        def lookup_original_text(query: str, top_k: int = 3) -> str:
            """根据关键词在原始章节中查找证据文本，返回最相关片段。"""
            q = (query or "").strip().lower()
            if not q:
                return "查询为空。"

            chunks = book_repository.load_chunks(book_id)
            scored: list[tuple[int, Chunk]] = []
            for chunk in chunks:
                chapter = (chunk.chapter or "").lower()
                text = (chunk.text or "").lower()
                score = 0
                if q in chapter:
                    score += 5
                score += text.count(q)
                if score > 0:
                    scored.append((score, chunk))

            if not scored:
                return "未在原文章节中找到匹配。"

            scored.sort(key=lambda x: x[0], reverse=True)
            selected = scored[: max(1, min(top_k, 6))]

            lines: list[str] = []
            for score, chunk in selected:
                snippet = (chunk.text or "")[:420].replace("\n", " ")
                lines.append(
                    f"[score={score}] {chunk.chapter or chunk.id}\n"
                    f"{snippet}"
                )
            return "\n\n".join(lines)

        @tool
        def vector_retrieve(query: str, top_k: int = 3) -> str:
            """对已分析叙事节点做向量检索，返回相关节点与原文线索。"""
            q = (query or "").strip()
            if not q:
                return "查询为空。"

            try:
                # 先尝试向量库检索
                results = vector_store.query_nodes(
                    book_id=book_id,
                    query_text=q,
                    n_results=max(1, min(top_k, 8))
                )
                if not results:
                    raise ValueError("No results from vector store")

                lines: list[str] = []
                for idx, doc in enumerate(results):
                    meta = doc.metadata or {}
                    scene = meta.get("scene", "")
                    situation = meta.get("situation", "")
                    original = (meta.get("original_text", "") or "").replace("\n", " ")[:320]
                    doc_text = (doc.page_content or "")[:120]
                    lines.append(
                        f"命中{idx + 1}: scene={scene}; situation={situation}\n"
                        f"node_text={doc_text}\n"
                        f"original={original}"
                    )
                return "\n\n".join(lines)
            except Exception:
                # 向量库不可用时，回退到 BookRepository 节点文本检索
                nodes = book_repository.load_nodes(book_id)
                q_lower = q.lower()
                fallback = []
                for n in nodes:
                    text = f"{n.scene} {n.situation} {n.turning_point}".lower()
                    if q_lower in text:
                        fallback.append(
                            f"scene={n.scene}; situation={n.situation}; turning={n.turning_point}"
                        )
                if not fallback:
                    return "向量检索失败，且节点回退检索未命中。"
                return "\n".join(fallback[: max(1, min(top_k, 8))])

        return [lookup_original_text, vector_retrieve]
