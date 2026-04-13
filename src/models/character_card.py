from pydantic import BaseModel, Field


class Relationship(BaseModel):
    """角色关系快照"""
    type: str = Field(default="neutral", description="tension/support/neutral")
    current_intensity: float = Field(default=0.0, description="0.0-1.0")
    history: list[dict] = Field(default_factory=list)


class EmotionalSnapshot(BaseModel):
    """情绪时间点"""
    node_id: str
    emotion: str


class CharacterCard(BaseModel):
    """跨节点累积的角色卡"""
    character_id: str
    name: str
    first_seen: str = ""
    current_state: str = ""
    total_appearances: int = 0
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    emotional_timeline: list[EmotionalSnapshot] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)

    def add_interaction(self, target: str, interaction_type: str, intensity_delta: float, node_id: str) -> None:
        if not target:
            return
        if target not in self.relationships:
            self.relationships[target] = Relationship(type=interaction_type or "neutral")
        rel = self.relationships[target]
        if interaction_type:
            rel.type = interaction_type
        rel.current_intensity = max(0.0, min(1.0, rel.current_intensity + float(intensity_delta)))
        rel.history.append({"node_id": node_id, "intensity": rel.current_intensity, "type": rel.type})

    def update_emotional_state(self, emotion: str, node_id: str) -> None:
        if not emotion:
            return
        self.current_state = emotion
        self.emotional_timeline.append(EmotionalSnapshot(node_id=node_id, emotion=emotion))

    def increment_appearance(self) -> None:
        self.total_appearances += 1

    def add_key_event(self, node_id: str) -> None:
        if node_id and node_id not in self.key_events:
            self.key_events.append(node_id)
