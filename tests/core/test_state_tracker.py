import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.state_tracker import StateTracker
from src.models.narrative_node import NarrativeNode, CharacterState


class TestStateTracker:
    def test_tracks_state_changes(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="calm")
            ],
            situation="John is in a dark room"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="scared")
            ],
            situation="John sees something unexpected"
        )

        delta = tracker.track(prev_node, curr_node)

        assert "John" in delta
        assert "calm" in delta
        assert "scared" in delta

    def test_tracks_new_character_entering(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="calm")
            ],
            situation="John is in a dark room"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="scared"),
                CharacterState(name="Maria", state_before="curious")
            ],
            situation="Maria enters the room"
        )

        delta = tracker.track(prev_node, curr_node)

        assert "Maria" in delta
        assert "enters scene" in delta

    def test_tracks_character_leaving(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="calm"),
                CharacterState(name="Maria", state_before="curious")
            ],
            situation="John and Maria are together"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="scared")
            ],
            situation="Maria leaves"
        )

        delta = tracker.track(prev_node, curr_node)

        assert "Maria" in delta
        assert "leaves scene" in delta

    def test_empty_delta_for_no_changes(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="calm")
            ],
            situation="John is calm"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="calm")
            ],
            situation="John looks around"
        )

        delta = tracker.track(prev_node, curr_node)

        assert delta == ""

    def test_empty_delta_when_no_prev_node(self):
        tracker = StateTracker()
        curr_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            location="A dark room",
            scene_timing="night",
            characters=[
                CharacterState(name="John", state_before="calm")
            ],
            situation="John enters"
        )

        delta = tracker.track(None, curr_node)

        assert delta == ""