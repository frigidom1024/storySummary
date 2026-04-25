# Agent4 Character Card Update Design

## Overview

Agent4 is responsible for maintaining character cards as chunks are processed. It receives chapter chunk text and narrative nodes (beats) from Agent1-3, uses LLM to analyze character interactions, emotions, and key events, then updates cumulative CharacterCards stored via BookRepository.

## Input

- `chunk.text`: Raw chapter text
- `nodes`: List of beats, each containing:
  - `id`: Beat ID
  - `scene`: Full scene description
  - `event_summary`: Summary of the event
  - `turning_point`: What changed
  - `characters`: List of CharacterStateModel (name only currently)
  - `thread_id`: Thread this node belongs to

## Output

Updated `CharacterCard` objects persisted to `BookRepository.characters.json`.

## CharacterCard Structure

```python
character_id: str      # Unique identifier (name)
name: str             # Display name
first_seen: str       # Node ID where character first appeared
first_seen_scene: str # Scene description of first appearance
current_state: str    # Most recent emotional/state description
total_appearances: int
relationships: dict[str, Relationship]
  - type: "tension" | "support" | "neutral"
  - current_intensity: float (0.0-1.0)
  - history: list[dict]
emotional_timeline: list[EmotionalSnapshot]
  - node_id: str
  - emotion: str
key_events: list[str] # Node IDs of significant moments
```

## Processing Flow

1. Load existing characters from `BookRepository.load_characters(book_id)`
2. For each node in the chunk:
   a. Identify characters present in `node.characters`
   b. For new characters: create CharacterCard with first_seen info
   c. Call LLM to analyze node and extract:
      - Emotional state changes
      - Character interactions (with target, type, intensity)
      - Whether this is a key event
3. Update cards using CharacterCard methods:
   - `add_interaction(target, type, intensity_delta, node_id)`
   - `update_emotional_state(emotion, node_id)`
   - `increment_appearance()`
   - `add_key_event(node_id)` if important
4. Save updated cards via `BookRepository.save_characters(book_id, characters)`

## LLM Analysis

### Prompt Strategy

The LLM receives:
- Current node's scene, event_summary, turning_point
- List of characters in this node
- Existing relationship context (from loaded CharacterCards)

The LLM outputs JSON describing:
```json
{
  "character_updates": [
    {
      "character": "CharacterName",
      "emotional_state": "紧张/平静/愤怒...",
      "is_key_event": true,
      "interactions": [
        {
          "target": "OtherCharacter",
          "type": "tension|support|neutral",
          "intensity_delta": 0.2
        }
      ]
    }
  ]
}
```

### Interaction Types

- **tension**: Conflict, argument, competition, distrust
- **support**: Cooperation, help, trust, affection
- **neutral**: No significant relationship change

### Intensity Scale

- 0.0-0.3: Minor interaction
- 0.4-0.6: Moderate interaction
- 0.7-1.0: Major/significant interaction

## Agent Implementation

### Class: Agent4CharacterCard

```python
class Agent4CharacterCard:
    def __init__(self, api_key: str = None, book_id: str = None):
        # Initialize LLM
        # Initialize BookRepository
        # self.characters: dict[str, CharacterCard] = {}

    async def process_nodes(self, nodes: list[dict], context: dict) -> dict:
        # Main entry point called by NarrativeNodeGenerator
        # nodes: beats from Agent1-3
        # context: {"chunk_id", "chunk_text", "chunk_order"}
        pass

    def get_all_characters(self) -> list[dict]:
        # Return all character cards as list of dicts

    def get_relationship_graph(self) -> dict:
        # Return relationship graph for visualization
```

### Tools

1. `get_previous_chunk_nodes()` - Returns nodes from latest processed chunk for context
2. `output_character_updates(updates: str)` - Final JSON output

### Error Handling

- **LLM disabled/unavailable**: Use algorithm defaults (increment appearances only)
- **Parse failure**: Log warning, skip that node's analysis
- **New character**: Create card with first_seen populated
- **No LLM result**: Still increment appearances for all characters in node

## Data Flow

```
Chunk + Nodes → Agent4.process_nodes()
                    ↓
            Load existing characters from BookRepository
                    ↓
            For each node: LLM analyzes interactions
                    ↓
            Update CharacterCard objects
                    ↓
            Save to BookRepository
                    ↓
            Return {"characters": [...], "relationship_graph": {...}
```

## Persistence

Characters are accumulated across all chunks in `BookRepository`:
- `load_characters(book_id)` - Load at start of each chunk
- `save_characters(book_id, characters)` - Save after each chunk

## Comparison with Agent1-3

| Agent | Input | Output | LLM Role |
|-------|-------|--------|----------|
| Agent1 | chunk.text | beats (nodes) | Extract narrative beats |
| Agent2 | beats | thread markers | Assign threads |
| Agent3 | beats | discussion_prompts | Generate prompts |
| Agent4 | chunk.text + beats | updated character cards | Analyze relationships/emotions |

## Key Design Decisions

1. **LLM analyzes per-node, not per-beat**: One LLM call per node in chunk (not per character), efficient
2. **Cumulative storage**: CharacterCards persist across chunks via BookRepository
3. **Graceful degradation**: Basic tracking works even without LLM
4. **Relationship directionality**: A→B interaction stored in A's card, not bidirectional
5. **Intensity deltas, not absolutes**: Each interaction adjusts intensity incrementally

## File Location

- `src/core/agents/agent4_character_card.py` (main implementation)
- Tests: `tests/core/test_character_tracker.py` (existing)
