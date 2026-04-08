MULTI_BEAT_NODE_PROMPT = """You are a narrative analyst. Extract ALL narrative beats from the given text.

IMPORTANT: A single chunk may contain multiple events, emotional shifts, or turning points. Extract EACH distinct beat as a separate node.

Respond ONLY with a valid JSON array of nodes (no markdown, no explanation):

```json
[
  {{
    "id": "n-{chunk_order}-{{beat_index}}",
    "parent_chunk_id": "chunk-{{chunk_order}}",
    "beat_index": 0,
    "scene": "Describe this specific moment's setting",
    "characters": [
      {{
        "name": "Character name",
        "state": "Current emotional/mental state",
        "goal": "What they want RIGHT NOW"
      }}
    ],
    "event": "What happens in THIS beat (1-2 sentences)",
    "dialogue_summary": "Key dialogue in THIS beat, or empty string",
    "tension": "What creates conflict in THIS beat",
    "stakes": "What's at risk in THIS beat",
    "foreshadow": "Hints about future, or empty string",
    "narrative_role": "opening/rising/climax/ending"
  }},
  {{
    "id": "n-{chunk_order}-{{beat_index}}",
    ...
  }}
]
```

Text to analyze:
{text}"""

STATE_CONTINUATION_PROMPT = """Analyze how character states evolve from the previous node to the current node.

Previous node summary:
- Characters: {prev_characters}
- Events: {prev_event}

Current node summary:
- Characters: {curr_characters}
- Events: {curr_event}

Output ONLY a JSON object describing state changes:

```json
{{
  "state_delta": "What changed: Maria: hopeful→desperate, goal: find husband→survive. John: confident→shaken"
}}
```

If no significant changes, output:
```json
{{"state_delta": ""}}
```"""

DETAIL_RECOVERY_PROMPT = """You are enriching a narrative summary with vivid details from the original text.

The summary loses these details - recover them:
- Sensory details (sounds, smells, textures, colors)
- Character mannerisms and physical reactions
- Environmental specifics
- Dialogue nuances and tone

Summary to enrich:
- Scene: {scene}
- Characters: {characters}
- Event: {event}

Original text for detail recovery:
{excerpt}

Output ONLY the enriched summary with recovered details (2-3 sentences, vivid and specific):"""

PODCAST_GENERATION_PROMPT = """You are a professional podcast storyteller. Using the provided narrative context, write an engaging podcast narration segment.

Current beat context:
- Scene: {scene}
- Characters: {characters}
- What happens: {event}
- Tension: {tension}
- Stakes: {stakes}

State evolution from previous: {state_delta}

Original text (for sensory details): {excerpt}

Write a 2-3 minute podcast narration that:
1. Sets the scene with vivid, sensory language
2. Paints character emotions and motivations
3. Shows character state evolution (not new characters every beat)
4. Builds tension naturally with rhythm
5. Uses conversational, spoken-word style

Output ONLY the narration text (no meta-comments)."""