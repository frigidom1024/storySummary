import pytest
from src.core.state_tracker import StateTracker
from src.models.narrative_node import NarrativeNode, CharacterState


class TestStateTracker:
    def test_tracks_state_changes(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="calm", goal="find the light")
            ],
            event="John enters the dark room"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="scared", goal="survive")
            ],
            event="Something moves in the shadows"
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
            characters=[
                CharacterState(name="John", state="calm", goal="find the light")
            ],
            event="John enters the dark room"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="scared", goal="survive"),
                CharacterState(name="Maria", state="curious", goal="explore")
            ],
            event="Maria enters the room"
        )

        delta = tracker.track(prev_node, curr_node)

        assert "Maria" in delta
        assert "enters scene" in delta

    def test_tracks_character_leaving(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="calm", goal="find the light"),
                CharacterState(name="Maria", state="curious", goal="explore")
            ],
            event="John and Maria are in the room"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="scared", goal="survive")
            ],
            event="Maria leaves"
        )

        delta = tracker.track(prev_node, curr_node)

        assert "Maria" in delta
        assert "leaves scene" in delta

    def test_empty_delta_for_no_changes(self):
        tracker = StateTracker()
        prev_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="calm", goal="find the light")
            ],
            event="John is in the room"
        )
        curr_node = NarrativeNode(
            id="n-2",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="calm", goal="find the light")
            ],
            event="John looks around"
        )

        delta = tracker.track(prev_node, curr_node)

        assert delta == ""

    def test_empty_delta_when_no_prev_node(self):
        tracker = StateTracker()
        curr_node = NarrativeNode(
            id="n-1",
            scene="A dark room",
            characters=[
                CharacterState(name="John", state="calm", goal="find the light")
            ],
            event="John enters"
        )

        delta = tracker.track(None, curr_node)

        assert delta == ""