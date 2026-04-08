from src.models.story_structure import StoryStructure
from src.models.narrative_node import NarrativeNode


class StructureBuilder:
    def build(self, nodes: list[NarrativeNode]) -> StoryStructure:
        story_structure = StoryStructure(
            linear_mainline=[node.id for node in nodes],
            opening=[],
            rising=[],
            climax=[],
            ending=[]
        )

        for node in nodes:
            role = node.narrative_role.lower().strip() if node.narrative_role else "rising"
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