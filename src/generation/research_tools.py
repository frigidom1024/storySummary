from __future__ import annotations

from langchain_core.tools import tool

from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.storage.vector_store import VectorStore


class ManuscriptResearchToolkit:
    """为写作 Agent 提供原文查找与向量检索工具。"""

    @staticmethod
    def create_tools(
        book_id: str,
        chunks: list[Chunk],
        nodes: list[NarrativeNode] | None = None,
        vector_path: str = "data/vectors",
    ):
        nodes = nodes or []
        vector_store = VectorStore(vector_path)

        @tool
        def lookup_original_text(query: str, top_k: int = 3) -> str:
            """根据关键词在原始章节中查找证据文本，返回最相关片段。"""
            q = (query or "").strip().lower()
            if not q:
                return "查询为空。"

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
                results = vector_store.search(query=q, book_id=book_id, n_results=max(1, min(top_k, 8)))
                metadatas = (results.get("metadatas") or [[]])[0]
                documents = (results.get("documents") or [[]])[0]
                if not metadatas:
                    return "向量库未命中结果。"

                lines: list[str] = []
                for idx, meta in enumerate(metadatas):
                    scene = meta.get("scene", "")
                    situation = meta.get("situation", "")
                    original = (meta.get("original_text", "") or "").replace("\n", " ")[:320]
                    doc = (documents[idx] if idx < len(documents) else "")[:120]
                    lines.append(
                        f"命中{idx + 1}: scene={scene}; situation={situation}\n"
                        f"node_text={doc}\n"
                        f"original={original}"
                    )
                return "\n\n".join(lines)
            except Exception:
                # 向量库不可用时，回退到节点文本检索
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
