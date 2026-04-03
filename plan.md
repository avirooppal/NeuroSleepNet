# NeuroSleepNet — Implementation Plan
### *The Drop-in Memory Layer That Actually Remembers*

---

## The Problem We're Solving

Every AI app today bolts on a memory layer as an afterthought. The existing solutions (mem0, Zep, custom vector stores) all share the same structural flaw:

- **They store facts, not context** — they remember *what* but forget *why* and *when*
- **They degrade silently** — older memories get buried or quietly evicted with no signal
- **They cause interference** — retrieved memories from Task A bleed into Task B responses
- **They require infrastructure overhead** — Redis, Pinecone, separate servers, separate billing
- **They're stateless between sessions at the model level** — memory is retrieved, not *consolidated*

**NeuroSleepNet's niche:** Long-running AI agents and copilots (coding assistants, customer support bots, personal productivity agents) that must serve the *same user* across hundreds of sessions without forgetting early context or confusing separate task threads.

**Target buyer:** Developers building AI-native SaaS products who are paying $0.50–$2.00/user/month on mem0 and still seeing regressions in agent quality after 30+ sessions.

---

## What NeuroSleepNet Actually Is (Sharpened Core Idea)

NeuroSleepNet is a **persistent, self-consolidating memory middleware** for LLM apps. It sits between your app and your LLM. You send it conversations. It handles storage, consolidation, retrieval, and interference prevention — returning a `memory_context` block you inject into your prompt.

The three biological mechanisms map to real engineering components:

| Biological Concept | Engineering Component | What It Solves |
|---|---|---|
| Sleep Replay | Async consolidation job | Merges redundant memories, resolves contradictions, compresses old sessions |
| Residual Pathways | Versioned memory graph with task anchors | Prevents old task memories from overwriting new ones |
| Task-Aware Attention | Retrieval scoring with task-context embedding | Returns only memories relevant to the *current task thread*, not all memories |

---

## Architecture (No Fluff)

```
Your App
   │
   ▼
NeuroSleepNet SDK  (pip install neurosleepnet)
   │
   ├─ write(session_id, user_id, messages[])   ← you call this after each turn
   ├─ read(session_id, user_id, query)          ← you call this before each LLM call
   └─ consolidate(user_id)                      ← runs async, you don't call it
   │
   ▼
NeuroSleepNet Server
   ├─ Ingestion Layer       — chunk, embed, tag with task_id
   ├─ Memory Graph Store    — nodes: facts/events, edges: task/time/relation
   ├─ Consolidation Engine  — nightly async job; merges, dedupes, decays stale nodes
   └─ Attention Retriever   — embedding similarity + task_id filter + recency decay
   │
   ▼
Returns:  { memory_context: string, task_threads: [], confidence: float }
```

**You inject `memory_context` directly into your system prompt. That's it.**

---

## Developer Integration — The 3-Line Promise

### Python (LangChain / raw OpenAI)

```python
from neurosleepnet import NeuroSleepClient

ns = NeuroSleepClient(api_key="nsk_...")

# Before LLM call — get relevant memory
memory = ns.read(user_id="u_123", query=user_message)

# Build your prompt
messages = [
    {"role": "system", "content": f"You are a helpful assistant.\n\n{memory.context}"},
    {"role": "user", "content": user_message}
]

# After LLM response — write to memory (fire and forget)
ns.write(user_id="u_123", messages=messages + [{"role": "assistant", "content": response}])
```

### JavaScript / Node

```javascript
import { NeuroSleepClient } from 'neurosleepnet';

const ns = new NeuroSleepClient({ apiKey: 'nsk_...' });

// Read
const memory = await ns.read({ userId: 'u_123', query: userMessage });

// Write (non-blocking)
ns.write({ userId: 'u_123', messages: conversationHistory });
```

### With LangChain Memory Interface (drop-in replacement)

```python
from neurosleepnet.integrations import NeuroSleepMemory

memory = NeuroSleepMemory(api_key="nsk_...", user_id="u_123")
# Drop into any existing LangChain chain as memory=memory
```

**Migration from mem0:** Change one import. The `.add()` and `.search()` method signatures are intentionally compatible.

---

## File & Folder Structure

```
neurosleepnet/
├── server/
│   ├── api/
│   │   ├── routes.py              # REST endpoints: /read, /write, /consolidate
│   │   └── auth.py                # API key validation
│   ├── core/
│   │   ├── ingestion.py           # Chunk + embed + tag incoming messages
│   │   ├── graph_store.py         # Memory graph: nodes, edges, versioning
│   │   ├── consolidation.py       # Sleep replay engine (async job)
│   │   ├── retriever.py           # Attention-weighted retrieval
│   │   └── task_detector.py       # Detect task thread shifts in conversation
│   ├── models/
│   │   ├── memory_node.py         # Pydantic model: fact, event, summary
│   │   └── task_thread.py         # Pydantic model: task context anchor
│   └── jobs/
│       └── nightly_consolidation.py  # Celery/APScheduler job
│
├── sdk/
│   ├── python/
│   │   ├── neurosleepnet/
│   │   │   ├── __init__.py
│   │   │   ├── client.py          # NeuroSleepClient: read(), write()
│   │   │   └── integrations/
│   │   │       ├── langchain.py   # LangChain memory adapter
│   │   │       └── llamaindex.py  # LlamaIndex memory adapter
│   │   └── setup.py
│   └── javascript/
│       ├── src/
│       │   └── index.ts
│       └── package.json
│
├── tests/
│   ├── unit/
│   │   ├── test_ingestion.py
│   │   ├── test_graph_store.py
│   │   ├── test_consolidation.py
│   │   └── test_retriever.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   └── test_sdk_integration.py
│   └── validation/
│       ├── validate_memory_quality.py   # Measures recall, precision on test scenarios
│       ├── validate_no_interference.py  # Ensures task A memories don't bleed into task B
│       ├── validate_consolidation.py    # Checks consolidation correctness over N sessions
│       └── benchmark_vs_mem0.py        # Side-by-side quality + latency comparison
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Core Module Specs

### `ingestion.py`
- Accept raw `messages[]` array (OpenAI format)
- Detect task thread using `task_detector.py` (embedding shift + keyword signal)
- Chunk into memory nodes: facts, events, preferences, instructions
- Embed with `text-embedding-3-small` (default) or configurable
- Tag each node: `user_id`, `task_id`, `session_id`, `timestamp`, `confidence`
- Write to graph store

### `graph_store.py`
- Backend: **SQLite** (default, zero-infra) or **PostgreSQL** (production)
- Nodes: memory items with embedding vector (stored as JSON blob or pgvector)
- Edges: `related_to`, `contradicts`, `supersedes`, `same_task`
- Versioning: never delete, only mark `superseded=True` — full audit trail
- Index: `(user_id, task_id, superseded)` for fast retrieval

### `consolidation.py` (The Sleep Engine)
- Runs as async background job (every N minutes or after M new writes)
- Steps:
  1. **Merge**: Find near-duplicate nodes (cosine sim > 0.92), merge into summary node
  2. **Resolve contradictions**: Flag nodes with `contradicts` edges, keep latest, mark older `superseded`
  3. **Decay**: Reduce `weight` of nodes not accessed in 30+ days
  4. **Summarize**: If a task thread has > 50 nodes, compress into 5–10 high-signal summary nodes
- All operations are logged to `consolidation_log` table for auditability

### `retriever.py`
- Input: `user_id`, `query` string, optional `task_hint`
- Embed query
- Score each memory node: `score = α·cosine_sim + β·task_match + γ·recency + δ·access_freq`
- Return top-K nodes formatted as a clean `memory_context` string
- Default token budget: 800 tokens (configurable per API key)
- Never return `superseded=True` nodes

---

## Test & Validation Scripts

### Unit Tests (`pytest tests/unit/`)

```
test_ingestion.py
  - test_chunks_long_conversation()
  - test_detects_task_shift()
  - test_embeds_and_tags_correctly()

test_graph_store.py
  - test_write_and_read_node()
  - test_supersede_on_contradiction()
  - test_versioning_audit_trail()

test_consolidation.py
  - test_merges_duplicates()
  - test_resolves_contradiction_keeps_latest()
  - test_decay_reduces_weight()
  - test_summarizes_large_task_thread()

test_retriever.py
  - test_returns_relevant_nodes()
  - test_respects_token_budget()
  - test_excludes_superseded_nodes()
  - test_task_isolation()
```

### Integration Tests (`pytest tests/integration/`)

```
test_api_endpoints.py
  - test_write_endpoint_200()
  - test_read_endpoint_returns_context()
  - test_auth_rejects_bad_key()
  - test_rate_limit_respected()

test_sdk_integration.py
  - test_python_client_write_read_cycle()
  - test_langchain_adapter_drop_in()
  - test_js_client_write_read_cycle()
```

### Validation Scripts (`python tests/validation/`)

**`validate_memory_quality.py`**
- Simulates 20 sessions for a synthetic user
- After each session, runs 10 factual recall questions
- Reports: recall@5, precision@5, F1
- Pass threshold: recall@5 > 0.80

**`validate_no_interference.py`**
- Creates user with 2 distinct task threads (e.g., "Python coding help" and "Meal planning")
- Writes 10 sessions to each thread
- Queries from thread A context, validates < 5% of returned nodes belong to thread B
- Pass threshold: cross-task contamination < 5%

**`validate_consolidation.py`**
- Writes 100 sessions with 30% deliberate contradictions and duplicates
- Runs consolidation engine
- Verifies: duplicate count reduced by > 80%, contradictions resolved to latest
- Pass threshold: all assertions green

**`benchmark_vs_mem0.py`**
- Runs identical test scenario against NeuroSleepNet and mem0 APIs
- Measures: recall@5, p50/p95 read latency, p50/p95 write latency, tokens returned
- Outputs side-by-side comparison table

---

## Pricing Strategy

**Guiding principle:** Undercut mem0 meaningfully on the entry tier, match on features, beat on quality.

| Tier | Price | Included | Overage |
|---|---|---|---|
| **Free** | $0/mo | 3 users, 500 writes/mo, 1K reads/mo | — |
| **Starter** | **$9/mo** | 50 users, 10K writes, 20K reads, SQLite backend | $0.80/1K writes |
| **Growth** | **$29/mo** | 500 users, 100K writes, 200K reads, Postgres backend, consolidation analytics | $0.60/1K writes |
| **Scale** | **$79/mo** | 5K users, 1M writes, 2M reads, priority consolidation, SLA 99.9% | $0.40/1K writes |
| **Enterprise** | Custom | Unlimited, self-host option, dedicated support | Custom |

**Comparison to mem0:**
- mem0 Starter: $19/mo for 1K memories
- NeuroSleepNet Starter: $9/mo for 10K writes with consolidation included
- Key differentiator: consolidation, task isolation, and interference prevention are **included at every paid tier** — mem0 requires custom implementation

**Self-host option** (Growth+): Docker Compose, bring your own Postgres + Redis. No per-user fees. One-time setup doc. This removes the infra objection from mid-market buyers.

---

## The Developer Pitch (README Hook)

```
mem0 stores memories.
NeuroSleepNet consolidates them.

Your agent after 10 sessions:    Fine with mem0
Your agent after 100 sessions:   Degraded with mem0, sharp with NeuroSleepNet

pip install neurosleepnet
```

---

## Pain Points Addressed (vs Existing Memory Layers)

| Pain Point | mem0 / Zep | NeuroSleepNet |
|---|---|---|
| Silent memory degradation over time | ❌ No mechanism | ✅ Consolidation engine runs async |
| Task thread cross-contamination | ❌ Flat vector store | ✅ Task-aware graph + attention retrieval |
| Contradictory memories returned | ❌ All retrieved equally | ✅ Contradiction resolution, only latest returned |
| Infra requirement | ❌ Needs Redis + vector DB | ✅ SQLite default, zero infra to start |
| Migration cost from existing setup | ❌ Full rewrite | ✅ mem0-compatible method signatures |
| Observability into memory state | ❌ Black box | ✅ Consolidation logs, memory graph API |
| Token bloat from stale memories | ❌ Returns top-K regardless | ✅ Decay scoring + token budget enforcement |

---

## Frontend Integration Notes (Since You Have This Ready)

Expose these endpoints from the server for your dashboard:

- `GET /dashboard/user/{user_id}/memory-graph` — visualize nodes + edges
- `GET /dashboard/user/{user_id}/task-threads` — list detected task threads
- `GET /dashboard/consolidation-log` — audit of consolidation runs
- `POST /dashboard/user/{user_id}/reset` — wipe and start fresh
- `GET /dashboard/metrics` — writes/reads/consolidations over time

These make the "memory health" dashboard a real selling point — developers can *see* what their agent remembers, which no competitor currently shows.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| API | FastAPI | Fast, typed, OpenAPI docs auto-generated |
| Embeddings | OpenAI `text-embedding-3-small` | Cheap, good, swappable |
| Graph/Store | SQLite → PostgreSQL | Zero infra to start, upgrade path clear |
| Vector search | `sqlite-vss` or `pgvector` | No separate vector DB needed |
| Background jobs | APScheduler (simple) / Celery (scale) | Start simple |
| SDK | Pure Python + TS, no heavy deps | Easy pip/npm install |
| Auth | API key (hashed, stored in DB) | Simple, familiar |
| Deployment | Docker Compose | One command start |

---

## Definition of Done (v1)

- [ ] `pip install neurosleepnet` works
- [ ] 3-line integration working end-to-end
- [ ] All unit + integration tests passing
- [ ] All 4 validation scripts passing their thresholds
- [ ] `benchmark_vs_mem0.py` shows NeuroSleepNet win on recall@5 and latency
- [ ] Docker Compose up in < 2 minutes
- [ ] mem0 migration guide published (1 page)
- [ ] Pricing page live with Free tier active
