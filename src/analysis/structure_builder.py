from src.models.story_structure import StoryStructure
from src.models.narrative_node import NarrativeNode


class StructureBuilder:
    """Build story structure from narrative nodes.

    Uses importance and position to infer narrative roles:
    - Opening: first 20% of nodes with importance < 0.5
    - Rising: importance 0.5-0.7
    - Climax: importance > 0.8 or turning_point indicates major change
    - Ending: last 20% of nodes
    """

    def build(self, nodes: list[NarrativeNode]) -> StoryStructure:
        if not nodes:
            return StoryStructure(
                linear_mainline=[],
                opening=[],
                rising=[],
                climax=[],
                ending=[]
            )

        story_structure = StoryStructure(
            linear_mainline=[node.id for node in nodes],
            opening=[],
            rising=[],
            climax=[],
            ending=[]
        )

        n = len(nodes)
        for i, node in enumerate(nodes):
            # Infer role from importance and position
            role = self._infer_role(node, i, n)
            if role == "opening":
                story_structure.opening.append(node.id)
            elif role == "rising":
                story_structure.rising.append(node.id)
            elif role == "climax":
                story_structure.climax.append(node.id)
            elif role == "ending":
                story_structure.ending.append(node.id)
            else:
                story_structure.rising.append(node.id)

        return story_structure

    def _infer_role(self, node: NarrativeNode, index: int, total: int) -> str:
        """Infer narrative role from node properties.

        - Climax: high importance (>0.8) or significant turning_point
        - Opening: first 20% with lower importance
        - Ending: last 20%
        - Rising: default
        """
        importance = node.importance if node.importance else 0.5

        # Check for climax indicators
        if importance > 0.8:
            return "climax"

        if node.turning_point and any(kw in node.turning_point for kw in ["转折", "突破", "揭露", "真相", "决裂", "表白"]):
            return "climax"

        # Position-based
        position_ratio = index / max(total - 1, 1)

        if position_ratio < 0.2 and importance < 0.5:
            return "opening"
        elif position_ratio > 0.8:
            return "ending"
        else:
            return "rising"
