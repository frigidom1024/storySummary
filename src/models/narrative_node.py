from pydantic import BaseModel, Field
from typing import Optional


class CharacterState(BaseModel):
    """角色在该节点进入时的状态（进入场景前）"""
    name: str
    state_before: str = ""  # 进入场景时的情绪/状态


class RelationshipStateChange(BaseModel):
    """一对角色在该节点中的关系变化"""
    pair: str = ""           # "陈屿-沈昭"
    from_state: str = ""     # 变化前
    to_state: str = ""       # 变化后


class NarrativeNode(BaseModel):
    # === 叙事坐标（可视化用）===
    id: str
    parent_chunk_id: str = ""
    beat_index: int = 0
    scene: str = ""                        # 完整场景："青岛路旧书店，下午三点多"
    location: str = ""                     # 简化地点："青岛路旧书店"
    scene_timing: str = ""                 # 时间段："午后"

    # === 角色在场（可视化用）===
    characters: list[CharacterState] = Field(default_factory=list)

    # === 叙事索引（播客用）===
    situation: str = ""          # 此刻的核心情境（1句话，不超过25字）
    turning_point: str = ""      # 转折点：这一刻发生了什么变化
    emotional_arc: str = ""      # 情绪弧："陈屿从[X]到[Y]"

    # === 元数据（播客用）===
    mood_tone: str = ""          # 氛围关键词："慵懒, 疏离, 忧郁"
    narrative_rhythm: str = ""   # slow / steady / fast / pause

    # === 讨论锚点（播客用）===
    discussion_prompts: list[str] = Field(default_factory=list)

    # === 关系状态（可视化用）===
    relationship_delta: list[RelationshipStateChange] = Field(default_factory=list)

    # === 链路（系统用）===
    prev_node_id: str = ""
    narrative_role: str = ""     # opening, rising, climax, ending

    # === 时间坐标 ===
    timeline_order: int = 0       # 故事时间顺序（负=回忆/前传，正=主线后）
    timeline_anchor: str = ""     # 时间锚点："大学时期", "毕业后一年", "现在"
    is_time_jump: bool = False   # 是否是时间跳跃
    jump_direction: str = ""     # "past"=跳到过去, "future"=跳到未来
    jump_label: str = ""         # "插叙", "倒叙", "前传", ""

    # === 叙事线链路 ===
    thread_id: str = "main"      # 叙事线ID："main", "zhang", "chenwei"
    thread_name: str = ""        # 叙事线名称："张医生的主线"
    thread_prev_node_id: str = ""  # 同一条叙事线上的前一个节点
    thread_next_node_id: str = ""  # 同一条叙事线上的下一个节点

    # === 分支/汇聚 ===
    branch_from_node: str = ""   # 从哪个节点分出这条支线
    converges_to_node: str = ""  # 汇聚到哪个节点
    is_convergence: bool = False # 是否是汇聚点

    def to_dict(self) -> dict:
        return self.model_dump()