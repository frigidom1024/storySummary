# Novel to Podcast MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a system that converts novel text into narrative nodes and generates podcast-ready storytelling content.

**Architecture:** A pipeline system with three critical enhancements:
1. **Multi-node per chunk**: One chunk → multiple narrative beats (sub-nodes)
2. **Detail Recovery**: Node → RAG检索原文 → Detail Enhancement → Podcast
3. **State Continuation**: Track character state evolution across nodes

Flow: Novel → Chunking → **[Multi-Beat Node Generation]** → Linear Structure → Storage → **[Detail Recovery + State Tracking]** → Podcast Generation

**Tech Stack:** Python 3.11+, Pydantic (data validation), ChromaDB (vector store), SQLite (metadata), OpenAI API (LLM), Python-dotenv

---

## Chunk 1: Project Foundation

### Task 1: Initialize Project Structure

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/models/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/storage/__init__.py`
- Create: `src/generation/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "story-summary"
version = "0.1.0"
description = "Convert novels to podcast-ready narrative structures"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "chromadb>=0.4.0",
    "openai>=1.0",
    "python-dotenv>=1.0",
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create src/models/narrative_node.py**

```python
from pydantic import BaseModel, Field
from typing import Optional


class CharacterState(BaseModel):
    name: str
    state: str = ""
    goal: str = ""


class NarrativeNode(BaseModel):
    id: str
    parent_chunk_id: str = ""  # Links to source chunk
    beat_index: int = 0  # Position within chunk (0, 1, 2... for multi-beat)
    scene: str
    characters: list[CharacterState] = Field(default_factory=list)
    event: str
    dialogue_summary: str = ""
    tension: str = ""
    stakes: str = ""
    foreshadow: str = ""
    narrative_role: str = ""  # opening, rising, climax, ending
    # State continuation fields
    prev_node_id: str = ""  # Link to previous node for state tracking
    state_delta: str = ""  # What changed: "John: scared→terrified, goal: escape→hide"

    def to_dict(self) -> dict:
        return self.model_dump()
```

- [ ] **Step 3: Create src/models/story_structure.py**

```python
from pydantic import BaseModel
from typing import Optional


class StoryStructure(BaseModel):
    linear_mainline: list[str] = Field(default_factory=list)  # node IDs in order
    opening: list[str] = Field(default_factory=list)
    rising: list[str] = Field(default_factory=list)
    climax: list[str] = Field(default_factory=list)
    ending: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()
```

- [ ] **Step 4: Create src/models/chunk.py**

```python
from pydantic import BaseModel


class Chunk(BaseModel):
    id: str
    text: str
    chapter: Optional[str] = None
    order: int = 0
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/models/ -v`
Expected: PASS (no tests yet - but imports should work)

- [ ] **Step 6: Commit**

```bash
git init && git add pyproject.toml src/
git commit -m "feat: project foundation with core data models"
```

---

### Task 2: Chunking System

**Files:**
- Create: `src/core/chunker.py`
- Create: `tests/core/test_chunker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_chunker.py
import pytest
from src.core.chunker import TextChunker, ChapterChunker


class TestTextChunker:
    def test_split_by_paragraphs(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunker = TextChunker(chunk_size=1)
        chunks = chunker.chunk(text)
        assert len(chunks) == 3
        assert chunks[0].text == "Paragraph one."

    def test_combines_small_paragraphs(self):
        text = "Short.\n\nAlso short."
        chunker = TextChunker(chunk_size=2)
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert "Short" in chunks[0].text


class TestChapterChunker:
    def test_extracts_chapters(self):
        text = "Chapter 1\n\nContent one.\n\nChapter 2\n\nContent two."
        chunker = ChapterChunker()
        chunks = chunker.chunk(text)
        assert len(chunks) == 2
        assert chunks[0].chapter == "Chapter 1"
        assert chunks[1].chapter == "Chapter 2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_chunker.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/chunker.py
import re
from typing import Iterator
from src.models.chunk import Chunk


class TextChunker:
    def __init__(self, chunk_size: int = 1):
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        for i, para in enumerate(paragraphs):
            chunks.append(Chunk(
                id=f"chunk-{i:04d}",
                text=para,
                order=i
            ))
        return chunks


class ChapterChunker:
    CHAPTER_PATTERN = re.compile(r'^Chapter\s+(\d+|[IVXLC]+)\s*$', re.MULTILINE | re.IGNORECASE)

    def chunk(self, text: str) -> list[Chunk]:
        lines = text.split("\n")
        chunks = []
        current_chapter = None
        current_content = []
        order = 0

        for line in lines:
            match = self.CHAPTER_PATTERN.match(line.strip())
            if match:
                if current_content:
                    chunks.append(Chunk(
                        id=f"chunk-{order:04d}",
                        text="\n\n".join(current_content),
                        chapter=current_chapter,
                        order=order
                    ))
                    order += 1
                    current_content = []
                current_chapter = line.strip()
            else:
                if line.strip():
                    current_content.append(line)

        if current_content:
            chunks.append(Chunk(
                id=f"chunk-{order:04d}",
                text="\n\n".join(current_content),
                chapter=current_chapter,
                order=order
            ))

        return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_chunker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/chunker.py tests/core/test_chunker.py
git commit -m "feat: add text and chapter chunking"
```

---

## Chunk 2: Narrative Node Generation (Core)

### Task 3: Narrative Node Prompt & Generator

**Files:**
- Create: `src/core/prompts.py`
- Create: `src/core/node_generator.py`
- Create: `tests/core/test_node_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_node_generator.py
import pytest
from unittest.mock import AsyncMock, patch
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.core.node_generator import NarrativeNodeGenerator


class TestNarrativeNodeGenerator:
    @pytest.mark.asyncio
    async def test_generates_multiple_beats_from_chunk(self):
        """One chunk → multiple narrative beats (multi-beat extraction)."""
        generator = NarrativeNodeGenerator(api_key="test-key")
        chunk = Chunk(id="c-001", text="John walked in. He was scared. Then he saw something.", order=0)

        with patch.object(generator.client.chat, 'completions', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value.choices = [
                type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''[
                          {"id":"n-0000-0","parent_chunk_id":"c-001","beat_index":0,"scene":"A room","characters":[{"name":"John","state":"calm","goal":"enter"}],"event":"John walks in","dialogue_summary":"","tension":"","stakes":"","foreshadow":"","narrative_role":"opening"},
                          {"id":"n-0000-1","parent_chunk_id":"c-001","beat_index":1,"scene":"A room","characters":[{"name":"John","state":"scared","goal":"understand situation"}],"event":"John sees something","dialogue_summary":"","tension":"fear","stakes":"safety","foreshadow":"","narrative_role":"rising"}
                        ]'''
                    })()
                })()
            ]
            nodes = await generator.generate_from_chunk(chunk)

        # Returns a LIST of nodes, not single node
        assert isinstance(nodes, list)
        assert len(nodes) == 2
        assert nodes[0].id == "n-0000-0"
        assert nodes[1].id == "n-0000-1"
        assert nodes[0].parent_chunk_id == "c-001"
        assert nodes[1].beat_index == 1
        assert nodes[0].characters[0].name == "John"
        assert nodes[1].characters[0].state == "scared"

    @pytest.mark.asyncio
    async def test_single_beat_still_returns_list(self):
        """Even a single beat returns a list for consistent handling."""
        generator = NarrativeNodeGenerator(api_key="test-key")
        chunk = Chunk(id="c-002", text="Simple sentence.", order=1)

        with patch.object(generator.client.chat, 'completions', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value.choices = [
                type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '{"id":"n-0001-0","parent_chunk_id":"c-002","beat_index":0,"scene":"A place","characters":[],"event":"Something happens","dialogue_summary":"","tension":"","stakes":"","foreshadow":"","narrative_role":""}'
                    })()
                })()
            ]
            nodes = await generator.generate_from_chunk(chunk)

        assert isinstance(nodes, list)
        assert len(nodes) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_node_generator.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write prompts module**

```python
# src/core/prompts.py

MULTI_BEAT_NODE_PROMPT = """You are a narrative analyst. Extract ALL narrative beats from the given text.

IMPORTANT: A single chunk may contain multiple events, emotional shifts, or turning points. Extract EACH distinct beat as a separate node.

Respond ONLY with a valid JSON array of nodes (no markdown, no explanation):

```json
[
  {{
    "id": "n-{chunk_order}-{beat_index}",
    "parent_chunk_id": "chunk-{chunk_order}",
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
    "id": "n-{chunk_order}-{beat_index}",
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
```

- [ ] **Step 4: Write multi-beat node generator**

```python
# src/core/node_generator.py
import json
from openai import AsyncOpenAI
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState
from src.core.prompts import MULTI_BEAT_NODE_PROMPT


class NarrativeNodeGenerator:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
        """Generate MULTIPLE narrative beats from ONE chunk."""
        prompt = MULTI_BEAT_NODE_PROMPT.format(
            text=chunk.text,
            chunk_order=chunk.order
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a narrative analyst that outputs valid JSON array."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n")[1:-1]
            content = "\n".join(content)
        data = json.loads(content)

        # Ensure we always return a list (even for single beat)
        if isinstance(data, dict):
            data = [data]

        nodes = []
        for beat_data in data:
            node = NarrativeNode(
                id=beat_data["id"],
                parent_chunk_id=chunk.id,
                beat_index=beat_data.get("beat_index", 0),
                scene=beat_data["scene"],
                characters=[CharacterState(**c) for c in beat_data.get("characters", [])],
                event=beat_data["event"],
                dialogue_summary=beat_data.get("dialogue_summary", ""),
                tension=beat_data.get("tension", ""),
                stakes=beat_data.get("stakes", ""),
                foreshadow=beat_data.get("foreshadow", ""),
                narrative_role=beat_data.get("narrative_role", "")
            )
            nodes.append(node)

        return nodes
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/core/test_node_generator.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/node_generator.py src/core/prompts.py tests/core/test_node_generator.py
git commit -m "feat: add narrative node generation with LLM"
```

---

### Task 4: Story Structure Organizer

**Files:**
- Create: `src/core/structure_builder.py`
- Create: `tests/core/test_structure_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_structure_builder.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_structure_builder.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write implementation**

```python
# src/core/structure_builder.py
from src.models.story_structure import StoryStructure
from src.models.narrative_node import NarrativeNode


class StructureBuilder:
    def build(self, nodes: list[NarrativeNode]) -> StoryStructure:
        story_structure = StoryStructure(
            linear_mainline=[node.id for node in nodes],
            opening=[],
            rising=[],
            climax=[],
            ending=[]
        )

        for node in nodes:
            role = node.narrative_role.lower().strip() if node.narrative_role else "rising"
            if role == "opening":
                story_structure.opening.append(node.id)
            elif role == "rising":
                story_structure.rising.append(node.id)
            elif role == "climax":
                story_structure.climax.append(node.id)
            elif role == "ending":
                story_structure.ending.append(node.id)
            else:
                story_structure.rising.append(node.id)

        return story_structure
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_structure_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/structure_builder.py tests/core/test_structure_builder.py
git commit -m "feat: add linear story structure builder"
```

---

## Chunk 3: Storage & RAG

### Task 5: Storage Layer (SQLite + ChromaDB)

**Files:**
- Create: `src/storage/database.py`
- Create: `src/storage/vector_store.py`
- Create: `tests/storage/test_database.py`
- Create: `tests/storage/test_vector_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_database.py
import pytest
import tempfile
import os
from src.storage.database import Database
from src.models.narrative_node import NarrativeNode, CharacterState


class TestDatabase:
    def test_save_and_retrieve_node(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(os.path.join(tmpdir, "test.db"))
            node = NarrativeNode(
                id="n-001",
                scene="A dark room",
                characters=[CharacterState(name="John", state="scared", goal="escape")],
                event="John entered the dark room",
                tension="Unknown danger",
                stakes="Life or death",
                narrative_role="opening"
            )
            db.save_node(node)
            retrieved = db.get_node("n-001")

            assert retrieved is not None
            assert retrieved.id == "n-001"
            assert retrieved.scene == "A dark room"
            assert len(retrieved.characters) == 1

    def test_save_and_retrieve_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.models.story_structure import StoryStructure
            db = Database(os.path.join(tmpdir, "test.db"))
            structure = StoryStructure(
                linear_mainline=["n-001", "n-002"],
                opening=["n-001"],
                rising=["n-002"]
            )
            db.save_structure("story-1", structure)
            retrieved = db.get_structure("story-1")

            assert retrieved is not None
            assert retrieved.linear_mainline == ["n-001", "n-002"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_database.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write database module**

```python
# src/storage/database.py
import sqlite3
import json
from pathlib import Path
from src.models.narrative_node import NarrativeNode, CharacterState
from src.models.story_structure import StoryStructure


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS structures (
                    story_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    story_id TEXT,
                    data TEXT NOT NULL
                )
            """)

    def save_node(self, node: NarrativeNode):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes (id, data) VALUES (?, ?)",
                (node.id, node.model_dump_json())
            )

    def get_node(self, node_id: str) -> NarrativeNode | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
            if row:
                return NarrativeNode.model_validate_json(row[0])
            return None

    def save_structure(self, story_id: str, structure: StoryStructure):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO structures (story_id, data) VALUES (?, ?)",
                (story_id, structure.model_dump_json())
            )

    def get_structure(self, story_id: str) -> StoryStructure | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM structures WHERE story_id = ?", (story_id,)
            ).fetchone()
            if row:
                return StoryStructure.model_validate_json(row[0])
            return None

    def save_chunk(self, story_id: str, chunk_id: str, text: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chunks (id, story_id, data) VALUES (?, ?, ?)",
                (chunk_id, story_id, json.dumps({"text": text}))
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_database.py -v`
Expected: PASS

- [ ] **Step 5: Write vector store**

```python
# src/storage/vector_store.py
import chromadb
from chromadb.config import Settings
from src.models.narrative_node import NarrativeNode


class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("narrative_nodes")

    def add_node(self, node: NarrativeNode, original_text: str):
        self.collection.add(
            ids=[node.id],
            documents=[f"{node.scene} {node.event} {node.dialogue_summary}"],
            metadatas=[{
                "scene": node.scene,
                "event": node.event,
                "original_text": original_text,
                "narrative_role": node.narrative_role
            }]
        )

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
```

- [ ] **Step 6: Commit**

```bash
git add src/storage/database.py src/storage/vector_store.py
git commit -m "feat: add SQLite and ChromaDB storage layer"
```

---

## Chunk 4: Content Generation

### Task 6: Detail Recovery & State Tracker

**Files:**
- Create: `src/core/detail_recovery.py`
- Create: `src/core/state_tracker.py`
- Create: `tests/core/test_detail_recovery.py`
- Create: `tests/core/test_state_tracker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_detail_recovery.py
import pytest
from unittest.mock import AsyncMock, patch
from src.core.detail_recovery import DetailRecovery


class TestDetailRecovery:
    @pytest.mark.asyncio
    async def test_enriches_node_with_details(self):
        recovery = DetailRecovery(api_key="test-key")
        excerpt = "The rain hammered against the window. John shivered, his teeth chattering."

        with patch.object(recovery.client.chat, 'completions', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value.choices = [
                type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': 'Rain lashed against the grimy window as John shuddered, his teeth clicking together involuntarily.'
                    })()
                })()
            ]
            enriched = await recovery.enrich(
                scene="Inside a room",
                characters="John (cold, wanting warmth)",
                event="John felt cold",
                excerpt=excerpt
            )

        assert "rain" in enriched.lower()
        assert "shivered" in enriched.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_detail_recovery.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write detail recovery module**

```python
# src/core/detail_recovery.py
from openai import AsyncOpenAI
from src.core.prompts import DETAIL_RECOVERY_PROMPT


class DetailRecovery:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def enrich(
        self,
        scene: str,
        characters: str,
        event: str,
        excerpt: str
    ) -> str:
        prompt = DETAIL_RECOVERY_PROMPT.format(
            scene=scene,
            characters=characters,
            event=event,
            excerpt=excerpt
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You enrich narrative summaries with vivid sensory details."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()
```

- [ ] **Step 4: Write state tracker**

```python
# src/core/state_tracker.py
from src.models.narrative_node import NarrativeNode


class StateTracker:
    def track(self, prev_node: NarrativeNode, curr_node: NarrativeNode) -> str:
        """Calculate state delta between two nodes."""
        if not prev_node:
            return ""

        deltas = []

        prev_chars = {c.name: c for c in prev_node.characters}
        curr_chars = {c.name: c for c in curr_node.characters}

        for name, curr_char in curr_chars.items():
            if name in prev_chars:
                prev_char = prev_chars[name]
                changes = []

                if prev_char.state != curr_char.state and curr_char.state:
                    changes.append(f"{prev_char.state}→{curr_char.state}")
                if prev_char.goal != curr_char.goal and curr_char.goal:
                    changes.append(f"goal: {prev_char.goal}→{curr_char.goal}")

                if changes:
                    deltas.append(f"{name}: {', '.join(changes)}")
            else:
                deltas.append(f"{name}: enters scene")

        for name in prev_chars:
            if name not in curr_chars:
                deltas.append(f"{name}: leaves scene")

        return "; ".join(deltas) if deltas else ""
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/core/test_detail_recovery.py tests/core/test_state_tracker.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/detail_recovery.py src/core/state_tracker.py
git commit -m "feat: add detail recovery and state tracking"
```

---

### Task 7: Podcast Generator with RAG

**Files:**
- Create: `src/generation/podcast_generator.py`
- Create: `tests/generation/test_podcast_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_podcast_generator.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.generation.podcast_generator import PodcastGenerator
from src.models.narrative_node import NarrativeNode, CharacterState


class TestPodcastGenerator:
    @pytest.mark.asyncio
    async def test_generates_podcast_segment(self):
        generator = PodcastGenerator(api_key="test-key")

        current_node = NarrativeNode(
            id="n-001",
            scene="A dark room with flickering candles",
            characters=[CharacterState(name="John", state="nervous", goal="find the exit")],
            event="John enters a dark room and hears a noise",
            dialogue_summary="",
            tension="Something lurks in the shadows",
            stakes="John's life is at risk",
            narrative_role="rising"
        )

        with patch.object(generator.client.chat, 'completions', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value.choices = [
                type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': "The room was dark, candles flickering against the walls..."
                    })()
                })()
            ]
            text = await generator.generate_segment(current_node, "John walked into the dark room.")

        assert "dark" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_podcast_generator.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write podcast generator**

```python
# src/generation/podcast_generator.py
from openai import AsyncOpenAI
from src.models.narrative_node import NarrativeNode
from src.storage.vector_store import VectorStore
from src.core.prompts import PODCAST_GENERATION_PROMPT
from src.core.detail_recovery import DetailRecovery


class PodcastGenerator:
    def __init__(self, api_key: str, vector_store: VectorStore = None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.vector_store = vector_store
        self.detail_recovery = DetailRecovery(api_key)

    def _format_characters(self, node: NarrativeNode) -> str:
        return ", ".join([
            f"{c.name} ({c.state}, goal: {c.goal})" for c in node.characters
        ])

    async def generate_segment(
        self,
        node: NarrativeNode,
        original_excerpt: str,
        prev_node: NarrativeNode = None,
        context_nodes: list[NarrativeNode] = None
    ) -> str:
        # Step 1: Recover details from original text
        enriched_scene = await self.detail_recovery.enrich(
            scene=node.scene,
            characters=self._format_characters(node),
            event=node.event,
            excerpt=original_excerpt
        )

        # Step 2: Get state delta for character evolution
        state_delta = node.state_delta if hasattr(node, 'state_delta') else ""

        # Step 3: Build context from previous nodes
        context = ""
        if prev_node:
            context = f"Previous beat: {prev_node.scene}. What happened: {prev_node.event}\n"
        if context_nodes:
            context += "Earlier context:\n" + "\n".join([
                f"- {n.scene}: {n.event}" for n in context_nodes[-2:]
            ])

        # Step 4: Generate podcast with all context
        prompt = PODCAST_GENERATION_PROMPT.format(
            scene=enriched_scene,
            characters=self._format_characters(node),
            event=node.event,
            tension=node.tension,
            stakes=node.stakes,
            state_delta=state_delta,
            excerpt=original_excerpt
        )

        if context:
            prompt = context + "\n\n" + prompt

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional podcast storyteller."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=800
        )

        return response.choices[0].message.content.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_podcast_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/podcast_generator.py tests/generation/test_podcast_generator.py
git commit -m "feat: add podcast generator with RAG context"
```

---

## Chunk 5: End-to-End Pipeline & CLI

### Task 7: Pipeline Orchestrator

**Files:**
- Create: `src/pipeline.py`
- Create: `src/cli.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.pipeline import NovelToPodcastPipeline


class TestPipeline:
    @pytest.mark.asyncio
    @patch('src.pipeline.OpenAI')
    async def test_full_pipeline_multi_beat(self, mock_openai_class):
        pipeline = NovelToPodcastPipeline(
            db_path=":memory:",
            vector_store_path=":memory:",
            api_key="test-key"
        )

        novel_text = """
        Chapter 1

        John walked into the dark room. His heart pounded. Then he heard a noise.
        """

        # Multi-beat returns a list of nodes
        with patch.object(pipeline.node_generator.client.chat, 'completions', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value.choices = [
                type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''[
                          {"id":"n-0001-0","parent_chunk_id":"chunk-0000","beat_index":0,"scene":"A dark room","characters":[{"name":"John","state":"scared","goal":"find light"}],"event":"John enters dark room","dialogue_summary":"","tension":"danger","stakes":"life","foreshadow":"","narrative_role":"opening"},
                          {"id":"n-0001-1","parent_chunk_id":"chunk-0000","beat_index":1,"scene":"A dark room","characters":[{"name":"John","state":"terrified","goal":"identify noise"}],"event":"John hears a noise","dialogue_summary":"","tension":"immediate threat","stakes":"life","foreshadow":"","narrative_role":"rising"}
                        ]'''
                    })()
                })()
            ]

            result = await pipeline.process(novel_text, title="Test Story")

        # Should have 2 nodes from 1 chunk (multi-beat)
        assert len(result["nodes"]) == 2
        assert result["nodes"][0].prev_node_id == ""
        assert result["nodes"][1].prev_node_id == "n-0001-0"
        assert result["nodes"][1].state_delta != ""
        assert result["structure"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write pipeline**

```python
# src/pipeline.py
from pathlib import Path
from src.core.chunker import ChapterChunker
from src.core.node_generator import NarrativeNodeGenerator
from src.core.structure_builder import StructureBuilder
from src.core.state_tracker import StateTracker
from src.storage.database import Database
from src.storage.vector_store import VectorStore
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.models.chunk import Chunk


class NovelToPodcastPipeline:
    def __init__(
        self,
        db_path: str,
        vector_store_path: str,
        api_key: str
    ):
        self.api_key = api_key
        self.chunker = ChapterChunker()
        self.node_generator = NarrativeNodeGenerator(api_key)
        self.structure_builder = StructureBuilder()
        self.state_tracker = StateTracker()
        self.db = Database(db_path)
        self.vector_store = VectorStore(vector_store_path)

    async def process(self, novel_text: str, title: str) -> dict:
        # 1. Chunk the novel
        chunks = self.chunker.chunk(novel_text)

        # 2. Generate MULTIPLE narrative nodes per chunk (multi-beat)
        all_nodes = []
        for chunk in chunks:
            # Each chunk can produce multiple nodes (beats)
            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]

            # Link nodes and track state
            prev_node = all_nodes[-1] if all_nodes else None

            for i, node in enumerate(nodes):
                node.prev_node_id = prev_node.id if prev_node else ""

                # Calculate state delta
                if prev_node:
                    node.state_delta = self.state_tracker.track(prev_node, node)

                # Save to storage
                self.db.save_node(node)
                self.db.save_chunk(title, chunk.id, chunk.text)
                self.vector_store.add_node(node, chunk.text)

                prev_node = node
                all_nodes.append(node)

        # 3. Build story structure
        structure = self.structure_builder.build(all_nodes)

        # 4. Save structure
        self.db.save_structure(title, structure)

        return {
            "title": title,
            "nodes": all_nodes,
            "structure": structure
        }
```

- [ ] **Step 4: Write CLI**

```python
# src/cli.py
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.pipeline import NovelToPodcastPipeline


async def main():
    parser = argparse.ArgumentParser(description="Convert novels to podcast narratives")
    parser.add_argument("input_file", type=Path, help="Path to novel text file")
    parser.add_argument("--title", required=True, help="Story title")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    parser.add_argument("--db", type=Path, default=Path("story_data.db"), help="Database path")
    parser.add_argument("--vector-store", type=Path, default=Path("vector_store"), help="Vector store path")

    args = parser.parse_args()

    load_dotenv()

    text = args.input_file.read_text(encoding="utf-8")

    pipeline = NovelToPodcastPipeline(
        db_path=str(args.db),
        vector_store_path=str(args.vector_store),
        api_key=os.getenv("OPENAI_API_KEY")
    )

    result = await pipeline.process(text, title=args.title)

    if args.output:
        import json
        args.output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"Processed {len(result['nodes'])} nodes")
    print(f"Structure: {result['structure'].model_dump()}")


if __name__ == "__main__":
    import os
    asyncio.run(main())
```

- [ ] **Step 5: Add .env.example**

```bash
# .env.example
OPENAI_API_KEY=your-api-key-here
```

- [ ] **Step 6: Commit**

```bash
git add src/pipeline.py src/cli.py .env.example
git commit -m "feat: add pipeline orchestrator and CLI"
```

---

### Task 8: Verify End-to-End

**Files:**
- Create: `samples/sample_chapter.txt` (test data)

- [ ] **Step 1: Create sample test data**

```text
Chapter 1: The Beginning

The old house stood at the end of the street, its windows dark and broken. Sarah approached slowly, her heart racing. She had heard the stories about this place.

Inside, dust particles floated through shafts of moonlight. The floorboards creaked under her weight. Each step felt like a decision between moving forward and turning back.

"Hello?" she called out, her voice trembling.

No answer came, only the echo of her own words. But somewhere in the darkness, she heard a faint whisper.
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add samples/sample_chapter.txt
git commit -m "test: add sample novel chapter for testing"
```

---

## Success Criteria

After completing this plan, you will have:

- [ ] **Working chunking** - Novels split into manageable narrative chunks
- [ ] **Multi-beat nodes** - One chunk → multiple narrative beats (solves "节点过粗" problem)
- [ ] **Rich narrative nodes** - Each beat becomes a structured unit with characters, tension, stakes, foreshadow
- [ ] **Detail Recovery** - Original text details recovered via RAG (solves "细节丢失" problem)
- [ ] **State Continuation** - Character state evolution tracked across nodes (solves "状态断裂" problem)
- [ ] **Linear story structure** - Nodes organized into opening/rising/climax/ending
- [ ] **Persistent storage** - SQLite + ChromaDB for nodes, chunks, and structure
- [ ] **RAG-enabled generation** - Context-aware podcast content generation
- [ ] **CLI interface** - `python -m src.cli input.txt --title "My Story"`

**Validation:** Run `python -m src.cli samples/sample_chapter.txt --title "Test Story"` and verify:
- Podcast has vivid sensory details (not generic)
- Character emotions evolve across beats (not reset each paragraph)
- Scene transitions feel continuous (not jumpy)
