from src.models.character_card import CharacterCard


def test_create_character_card():
    card = CharacterCard(character_id="陈屿", name="陈屿", first_seen="n-0-0", current_state="无聊")
    assert card.total_appearances == 0
    assert card.relationships == {}
    assert card.emotional_timeline == []


def test_update_relationship():
    card = CharacterCard(character_id="陈屿", name="陈屿", first_seen="n-0-0")
    card.add_interaction("老板", "tension", 0.3, "n-0-1")
    assert "老板" in card.relationships
    assert card.relationships["老板"].current_intensity == 0.3


def test_emotional_timeline_append():
    card = CharacterCard(character_id="陈屿", name="陈屿", first_seen="n-0-0")
    card.update_emotional_state("无聊", "n-0-0")
    card.update_emotional_state("微妙", "n-1-1")
    assert len(card.emotional_timeline) == 2
