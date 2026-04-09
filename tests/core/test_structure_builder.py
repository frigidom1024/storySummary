import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.structure_builder import StructureBuilder
from src.models.narrative_node import NarrativeNode, CharacterState


class TestStructureBuilder:
    def test_creates_linear_mainline(self):
        nodes = [
            NarrativeNode(id="n-001", scene="s1", event="e1", narrative_role="opening"),
            NarrativeNode(id="n-002", scene="s2", event="e2", narrative_role="rising"),
            NarrativeNode(id="n-003", scene="s3", event="e3", narrative_role="climax"),
            NarrativeNode(id="n-004", scene="s4", event="e4", narrative_role="ending"),
        ]
        builder = StructureBuilder()
        structure = builder.build(nodes)

        assert structure.linear_mainline == ["n-001", "n-002", "n-003", "n-004"]
        assert structure.opening == ["n-001"]
        assert structure.rising == ["n-002"]
        assert structure.climax == ["n-003"]
        assert structure.ending == ["n-004"]

    def test_labels_unlabeled_nodes_as_rising(self):
        nodes = [
            NarrativeNode(id="n-001", scene="s1", event="e1", narrative_role="opening"),
            NarrativeNode(id="n-002", scene="s2", event="e2", narrative_role=""),
        ]
        builder = StructureBuilder()
        structure = builder.build(nodes)

        assert structure.rising == ["n-002"]