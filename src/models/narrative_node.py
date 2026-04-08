from pydantic import BaseModel, Field
from typing import Optional


class CharacterState(BaseModel):
    name: str
    state: str = ""
    goal: str = ""


class NarrativeNode(BaseModel):
    id: str
    parent_chunk_id: str = ""  # Links to source chunk
    beat_index: int = 0  # Position within chunk (0, 1, 2... for multi-beat)
    scene: str
    characters: list[CharacterState] = Field(default_factory=list)
    event: str
    dialogue_summary: str = ""
    tension: str = ""
    stakes: str = ""
    foreshadow: str = ""
    narrative_role: str = ""  # opening, rising, climax, ending
    # State continuation fields
    prev_node_id: str = ""  # Link to previous node for state tracking
    state_delta: str = ""  # What changed: "John: scared→terrified, goal: escape→hide"

    def to_dict(self) -> dict:
        return self.model_dump()