from src.analysis.character_tracker import CharacterTracker


def test_create_character_on_first_seen():
    tracker = CharacterTracker()
    nodes = [{"id": "n-0-0", "characters": [{"name": "陈屿", "state_before": "无聊"}]}]
    tracker.process_nodes(nodes)
    assert "陈屿" in tracker.characters
    assert tracker.characters["陈屿"].first_seen == "n-0-0"


def test_accumulate_interactions():
    tracker = CharacterTracker()
    nodes = [
        {
            "id": "n-0-0",
            "characters": [{"name": "陈屿", "state_before": "无聊"}],
            "interactions": [{"target": "老板", "type": "tension", "intensity_delta": 0.3}],
        }
    ]
    tracker.process_nodes(nodes)
    assert "老板" in tracker.characters["陈屿"].relationships


def test_key_events_for_high_importance():
    tracker = CharacterTracker()
    nodes = [{"id": "n-0-0", "characters": [{"name": "陈屿"}], "importance": 0.85}]
    tracker.process_nodes(nodes)
    assert "n-0-0" in tracker.characters["陈屿"].key_events
