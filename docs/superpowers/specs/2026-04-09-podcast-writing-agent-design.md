# Podcast Writing Agent Design

**Date:** 2026-04-09
**Status:** Approved

---

## 1. Overview

Design an autonomous agent that generates podcast-style manuscript ("聊一聊" commentary) from a novel's narrative index nodes (NarrativeNode) and original text chunks.

**Input:** A book (EPUB/PDF) processed through existing pipeline → Chunk[] + NarrativeNode[]

**Output:** A complete podcast manuscript with storyline summary + personal reflection, in the "聊一聊" spoken style.

**Core Principle:** Each Chunk is processed with its full original text loaded. No vector retrieval during writing — simplicity and context clarity over sophisticated retrieval.

---

## 2. Architecture

```
Pipeline (existing)
  └─→ BookReader (EPUB/PDF)
        └─→ ChapterChunker → Chunk[]
              └─→ NarrativeNodeGenerator → NarrativeNode[] per chunk

PodcastWritingAgent (new)
  └─→ Reads: all NarrativeNode + all Chunk original text
        └─→ Phase 1: Planning (read indexes only)
        └─→ Phase 2: Write by Chunk order (full chunk text + nodes)
        └─→ Phase 3: Polish & merge
        └─→ Output: PodcastManuscript
```

**Key constraint:** No vector search during writing. Each Chunk's original text is loaded directly.

---

## 3. Agent Workflow (3 Phases)

### Phase 1 — Planning (Read Indexes Only)

Read all NarrativeNode WITHOUT original text.

**Purpose:**
- Analyze narrative structure (opening → rising → climax → ending)
- Determine chapter segmentation and narrative order
- Establish overall tone and thematic direction

**Output:** Writing outline written to state file.

### Phase 2 — Write by Chunk Order

Process chunks sequentially. For each chunk:

1. Read state file to know "what has been established" and "current progress"
2. Load: full chunk original text + that chunk's NarrativeNode list
3. Generate podcast manuscript section based on NarrativeNode (situation, turning_point, emotional_arc, etc.)
4. Update state file after each chunk (progress + established claims)

**State file records:**
- Current chunk index
- Written chapter manuscripts (list)
- Established core claims (to avoid repetition and contradiction)

**Writing style guidance:**
- Spoken, conversational ("聊一聊" style)
- Include vivid details from original text as reference material (not read verbatim)
- Add personal reflection and thematic exploration
- Natural transitions between beats

### Phase 3 — Polish & Merge

Input: all written chapter manuscripts.

**Purpose:**
- Remove content duplication across chapters
- Unify spoken style and tone
- Add inter-chapter transitions
- Strengthen personal reflection and thematic conclusion

**Output:** Complete podcast manuscript (string).

---

## 4. State File Design

File: `output/{book_title}/writing_state.json`

```json
{
  "book_title": "书名",
  "phase": "planning | writing | polishing | done",
  "outline": {
    "chapters": [
      {
        "chunk_id": "chunk-0001",
        "title": "章节标题",
        "summary": "章节核心内容概述"
      }
    ],
    "overall_tone": "整体基调描述",
    "core_themes": ["主题1", "主题2"]
  },
  "written_chapters": [
    {
      "chunk_id": "chunk-0001",
      "manuscript": "章节稿子全文"
    }
  ],
  "current_chunk_index": 0,
  "established_claims": [
    "已确立的核心观点1",
    "已确立的核心观点2"
  ]
}
```

State file is written after each chapter completion. Agent can resume from断点 (checkpoint) on restart.

---

## 5. Prompt Strategy Per Chapter

When generating a chapter manuscript, the prompt contains:

1. **Established claims from previous chapters** (from state file)
2. **NarrativeNode list for this chunk** (situation, turning_point, emotional_arc, relationship_delta, etc.)
3. **Full original text of this chunk** (as reference material)
4. **Writing instructions** (spoken style, conversational tone, include reflection)

The original text is used as "reference material" — Agent pulls vivid details, not reading content verbatim.

---

## 6. Output Format

```python
class PodcastManuscript:
    metadata: {
        "title": str,
        "author": str,
        "total_chapters": int,
        "estimated_duration": str  # e.g., "25分钟"
    }
    chapters: list[{
        "chunk_id": str,
        "title": str,
        "manuscript": str  # full chapter manuscript
    }]
    full_manuscript: str  # all chapters merged
```

---

## 7. Key Design Decisions

| Decision | Choice | Reason |
|---------|--------|--------|
| Memory management | External JSON state file | Simple, restartable from checkpoint |
| Text retrieval during writing | Direct chunk loading, no vector search | Clean context, no retrieval noise |
| Chunk processing order | Sequential by Chunk order | Natural narrative flow, easy to track progress |
| Final output | Agent fully autonomous, JSON state + manuscript | User reviews after completion |
| Writing style | "聊一聊" conversational | As per product example |

---

## 8. Files to Create

```
src/generation/
  podcast_writing_agent.py   # Main agent class
  manuscript.py             # PodcastManuscript model

tests/generation/
  test_podcast_writing_agent.py
```

---

## 9. Implementation Notes

- Use existing `Chunk` and `NarrativeNode` models (no changes needed)
- State file written after each chapter to enable resume
- Phase 1 prompt should emphasize structural analysis, not content generation
- Phase 3 (polish) is a separate LLM call after all chapters written
- Estimated chapter count = number of Chunks with significant narrative nodes
