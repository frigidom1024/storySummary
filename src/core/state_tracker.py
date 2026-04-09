from src.models.narrative_node import NarrativeNode


class StateTracker:
    def track(self, prev_node: NarrativeNode, curr_node: NarrativeNode) -> str:
        """Calculate state delta between two nodes."""
        if prev_node is None:
            return ""

        deltas = []

        prev_chars = {c.name: c for c in prev_node.characters}
        curr_chars = {c.name: c for c in curr_node.characters}

        for name, curr_char in curr_chars.items():
            if name in prev_chars:
                prev_char = prev_chars[name]
                changes = []

                if prev_char.state_before != curr_char.state_before and curr_char.state_before:
                    changes.append(f"{prev_char.state_before}→{curr_char.state_before}")

                if changes:
                    deltas.append(f"{name}: {', '.join(changes)}")
            else:
                deltas.append(f"{name}: enters scene")

        for name in prev_chars:
            if name not in curr_chars:
                deltas.append(f"{name}: leaves scene")

        return "; ".join(deltas) if deltas else ""