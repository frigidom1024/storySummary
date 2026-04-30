from __future__ import annotations

from pydantic import BaseModel, Field


class CharacterStateModel(BaseModel):
    """Character state schema for structured output."""
    name: str = Field(description="Character name")


class NarrativeNode(BaseModel):
    """Single narrative beat schema - 叙事索引卡."""
    #agent1_extractor fields
    id: str = Field(description="Unique beat ID")
    beat_index: int = Field(description="Position within chunk (0, 1, 2...)")
    scene: str = Field(description="Full scene description e.g. '青岛路旧书店，下午三点多'")
    location: str = Field(default="", description="Simplified location name")
    scene_timing: str = Field(default="", description="Time period: 午后/傍晚/夜间 etc")
    characters: list[CharacterStateModel] = Field(default_factory=list, description="Characters present in this beat")
    event_summary: str = Field(default="", description="Summary of the event in this beat")
    situation: str = Field(default="", description="Core situation in one sentence, max 25 chars")
    turning_point: str = Field(default="", description="What changed in this beat, or '渐变：...'")
    importance: float = Field(default=0.5, description="Node importance 0.0-1.0 for visualization node size")
    time_label: str = Field(default="", description="Time label: NOW, PAST, FUTURE")


    #agent_time_marker fields
    thread_id: str = Field(default="", description="Thread ID: main etc")
    thread_name: str = Field(default="", description="Thread name")
    thread_prev_node_id: str = Field(default="", description="Previous node ID in same thread")
    thread_next_node_id: str = Field(default="", description="Next node ID in same thread (optional)")

    # deprecated: moved to Chunk level, kept for backward compatibility
    discussion_prompts: list[str] = Field(default_factory=list, description="[DEPRECATED] Discussion anchors - moved to Chunk.discussion_prompts")

    # parent chunk reference
    parent_chunk_id: str = Field(default="", description="Parent chunk ID this node belongs to")

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_ToolResponseNode(self) -> ToolResponseNode:
        return ToolResponseNode(
            id=self.id,
            time_label=self.time_label or "",
            scene=self.scene or "",
            thread_id=self.thread_id or "main",
            characters=[c.name for c in self.characters if c.name],
            event_summary=self.event_summary or "",
            situation=self.situation or "",
            importance=float(self.importance),
        )



    def to_vector_content(self) -> tuple[str, dict]:
        """return the content and metadata for vector store"""
        return self.scene + " " + self.event_summary + " " + self.situation+" ".join([c.name for c in self.characters]), {
            "node_id": self.id,
            "position": self.beat_index,
            "thread_id": self.thread_id,
        }

class ToolResponseNode(BaseModel):
    """Node summary for tool response"""
    id: str = Field(description="Unique beat ID")
    time_label: str = Field(description="Time label: NOW, PAST, FUTURE")
    scene: str = Field(description="Full scene description e.g. '青岛路旧书店，下午三点多'")
    thread_id: str = Field(description="Thread ID: main etc")
    characters: list[str] = Field(description="Characters present in this beat")
    event_summary: str = Field(description="Summary of the event in this beat")
    situation: str = Field(description="Core situation in one sentence, max 25 chars")
    importance: float = Field(description="Node importance 0.0-1.0 for visualization node size")
    time_label: str = Field(default="", description="Time label: NOW, PAST, FUTURE")

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def get_docs(cls) -> str:
        docs = []
        for name, field in cls.model_fields.items():
            docs.append(f"{name}: {field.description}")
        return "\n".join(docs)

class VectorSearchNode(BaseModel):
    scene: str = Field(description="Full scene description e.g. '青岛路旧书店，下午三点多'")
    event_summary: str = Field(description="Summary of the event in this beat")
    situation: str = Field(description="Core situation in one sentence, max 25 chars")
    characters: list[str] = Field(description="Characters present in this beat")

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def get_docs(cls) -> str:
        docs = []
        for name, field in cls.model_fields.items():
            docs.append(f"{name}: {field.description}")
        return "\n".join(docs)