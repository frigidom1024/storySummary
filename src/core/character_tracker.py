import logging
from src.models.character_card import CharacterCard

from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class CharacterTracker:
    """跨 chunk 维护角色卡状态"""

    def __init__(self):
        self.characters: dict[str, CharacterCard] = {}

    def process_nodes(self, nodes: list[dict]) -> None:
        debug_log("char_tracker", "process_nodes called with {} nodes, current char count={}", len(nodes), len(self.characters))
        for node in nodes:
            self._process_node(node)
        debug_log("char_tracker", "After processing: {} characters tracked", len(self.characters))

    def _process_node(self, node: dict) -> None:
        characters = node.get("characters", [])
        interactions = node.get("interactions", [])
        node_id = node.get("id", "")
        importance = float(node.get("importance", 0.5))

        debug_log("char_tracker", "  Processing node_id={} chars={} interactions={} importance={}",
                  node_id, [c.get("name") for c in characters], len(interactions), importance)

        names = [c.get("name", "") for c in characters if c.get("name")]
        for char in characters:
            name = char.get("name", "")
            if not name:
                continue
            if name not in self.characters:
                self.characters[name] = CharacterCard(
                    character_id=name,
                    name=name,
                    first_seen=node_id,
                    current_state=char.get("state_before", ""),
                )
                debug_log("char_tracker", "    New character: {} first_seen={}", name, node_id)
            card = self.characters[name]
            card.increment_appearance()
            if char.get("state_before"):
                card.update_emotional_state(char["state_before"], node_id)
            if importance >= 0.8:
                card.add_key_event(node_id)
                debug_log("char_tracker", "    Key event added for {} at {}", name, node_id)

        source_char = names[0] if names else ""
        for interaction in interactions:
            debug_log("char_tracker", "    Interaction: {} -> {} type={} delta={}",
                      source_char, interaction.get("target"), interaction.get("type"), interaction.get("intensity_delta"))
            if source_char and source_char in self.characters:
                self.characters[source_char].add_interaction(
                    target=interaction.get("target", ""),
                    interaction_type=interaction.get("type", "neutral"),
                    intensity_delta=float(interaction.get("intensity_delta", 0.0)),
                    node_id=node_id,
                )

    def get_character(self, name: str) -> CharacterCard | None:
        return self.characters.get(name)

    def get_all_characters(self) -> dict[str, CharacterCard]:
        return self.characters

    def get_relationship_graph(self) -> dict:
        nodes = []
        edges = []
        for char_name, card in self.characters.items():
            nodes.append({"id": char_name, "name": char_name, "total_appearances": card.total_appearances})
            for target, rel in card.relationships.items():
                edges.append(
                    {
                        "source": char_name,
                        "target": target,
                        "type": rel.type,
                        "intensity": rel.current_intensity,
                    }
                )
        return {"nodes": nodes, "edges": edges}
