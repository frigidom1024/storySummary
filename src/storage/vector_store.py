import chromadb
from chromadb.config import Settings
from src.models.narrative_node import NarrativeNode


class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("narrative_nodes")

    def add_node(self, node: NarrativeNode, original_text: str, book_id: str = None):
        """Add a narrative node to the vector store.

        Args:
            node: NarrativeNode to store
            original_text: The original text chunk content
            book_id: The book this node belongs to (for isolation)
        """
        metadata = {
            "scene": node.scene,
            "location": node.location,
            "situation": node.situation,
            "turning_point": node.turning_point,
            "emotional_arc": node.emotional_arc,
            "mood_tone": node.mood_tone,
            "narrative_role": node.narrative_role,
            "original_text": original_text,
        }
        if book_id:
            metadata["book_id"] = book_id

        self.collection.add(
            ids=[node.id],
            documents=[f"{node.scene} {node.situation} {node.turning_point}"],
            metadatas=[metadata]
        )

    def search(self, query: str, book_id: str = None, n_results: int = 3) -> list[dict]:
        """Search for similar nodes.

        Args:
            query: Search query text
            book_id: Optional - if set, only search within this book
            n_results: Number of results to return

        Returns:
            ChromaDB query results dict
        """
        if book_id:
            # Filter by book_id using where clause
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"book_id": book_id}
            )
        else:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
        return results
