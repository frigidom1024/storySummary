import chromadb
from chromadb.config import Settings
from src.models.narrative_node import NarrativeNode


class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("narrative_nodes")

    def add_node(self, node: NarrativeNode, original_text: str):
        self.collection.add(
            ids=[node.id],
            documents=[f"{node.scene} {node.situation} {node.turning_point}"],
            metadatas=[{
                "scene": node.scene,
                "location": node.location,
                "situation": node.situation,
                "turning_point": node.turning_point,
                "emotional_arc": node.emotional_arc,
                "mood_tone": node.mood_tone,
                "narrative_role": node.narrative_role,
                "original_text": original_text
            }]
        )

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results