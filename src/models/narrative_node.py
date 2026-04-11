from pydantic import BaseModel, Field


class CharacterState(BaseModel):
    """角色在该节点进入时的状态"""
    name: str
    state_before: str = ""


class RelationshipStateChange(BaseModel):
    """一对角色在该节点中的关系变化"""
    pair: str = ""
    from_state: str = ""
    to_state: str = ""


class NarrativeNode(BaseModel):
    id: str
    parent_chunk_id: str = ""
    beat_index: int = 0
    scene: str = ""
    location: str = ""
    scene_timing: str = ""
    characters: list[CharacterState] = Field(default_factory=list)
    situation: str = ""
    turning_point: str = ""
    emotional_arc: str = ""
    mood_tone: str = ""
    narrative_rhythm: str = ""
    discussion_prompts: list[str] = Field(default_factory=list)
    relationship_delta: list[RelationshipStateChange] = Field(default_factory=list)
    prev_node_id: str = ""
    narrative_role: str = ""
    timeline_order: int = 0
    timeline_anchor: str = ""
    is_time_jump: bool = False
    jump_direction: str = ""
    jump_label: str = ""
    thread_id: str = "main"
    thread_name: str = ""
    thread_prev_node_id: str = ""
    thread_next_node_id: str = ""
    branch_from_node: str = ""
    converges_to_node: str = ""
    is_convergence: bool = False

    def to_dict(self) -> dict:
        return self.model_dump()