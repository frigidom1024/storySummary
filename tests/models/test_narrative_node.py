from src.models.narrative_node import NarrativeNode, InteractionModel


def test_importance_normalized_to_float():
    node = NarrativeNode(id="n-0-0", importance=0.75)
    assert isinstance(node.importance, float)
    assert 0.0 <= node.importance <= 1.0


def test_importance_defaults():
    node = NarrativeNode(id="n-0-0")
    assert node.importance == 0.5


def test_interactions_field():
    node = NarrativeNode(
        id="n-0-0",
        interactions=[InteractionModel(target="老板", type="tension", intensity_delta=0.3)],
    )
    assert len(node.interactions) == 1
    assert node.interactions[0].target == "老板"
