> ⚠️ **REBUILD NOTICE**
> The **public API surface, architecture, and package structure** must be rebuilt from scratch to match this plan exactly.
> Any existing code, endpoints, or SDK functions that do not match this spec must be deleted and rewritten — not patched.
>
> **What this means in practice:**
> - Rewrite `__init__.py` completely — no legacy function signatures survive
> - Working infrastructure (FastAPI, Qdrant, PostgreSQL, Redis, Docker Compose, React dashboard) may be retained and upgraded, not thrown away
> - Every new or modified component must conform to this plan's spec — nothing carried over unchecked
> - The public API is the contract. The internals serve it, not the other way around
>
> **Package naming:**
> - The package is named `neurosleepnet` in `pyproject.toml`
> - An `nsn/` directory inside the SDK re-exports everything: `from neurosleepnet import *`
> - `pip install neurosleepnet` → `import nsn` works. Both names resolve to the same library.
>
> The name of this project is **NeuroSleepNet**. The import alias is `nsn`.

---

# NeuroSleepNet — Memory Layer for AI Agents
> Sleep-inspired persistent memory for Small Language Models. Plug in 3 lines. Outperform LLMs on your domain.

```python
import nsn
nsn.init(project="my-agent")
agent = nsn.wrap(your_slm)
```

---

## 1. The Name & Concept

**NeuroSleepNet** (imported as `nsn`)

Inspired by how the human brain consolidates memory during sleep — NeuroSleepNet gives AI agents the same biological advantage: instead of forgetting everything between sessions, agents *consolidate*, *prioritize*, and *recall* what matters most.

The three pillars of the human brain's memory system map directly onto NeuroSleepNet's architecture:

| Brain Mechanism | NeuroSleepNet Equivalent | What It Does |
|---|---|---|
| **Sleep Replay** | Sleep Engine | Periodically replays past experiences to reinforce knowledge |
| **Residual Pathways** | Stable Memory Channels | Preserves learned representations across tasks without overwriting |
| **Attention Focus** | Task-Aware Retrieval | Dynamically surfaces only the most relevant memories per query |

---

## 2. The Problem Space

### Why SLMs Fail Without NeuroSleepNet
| Pain Point | Root Cause | NeuroSleepNet Fix |
|---|---|---|
| Forget context between sessions | No persistent memory | Episodic store + sleep consolidation |
| Repeat questions already answered | No user-scoped recall | Per-user memory scoping |
| Catastrophic forgetting on new tasks | No residual pathways | Residual memory channels |
| Bad domain reasoning | No knowledge accumulation | Semantic memory + sleep replay |
| Hallucinate known facts | No grounded retrieval | Task-aware retrieval + confidence threshold |
| Can't learn from mistakes | No feedback loop | Implicit behavioral feedback + `nsn.feedback()` |
| Hard rules silently forgotten | No permanent memory primitive | `nsn.pin()` — immutable, always-injected |
| Wrong memory injected confidently | No recall confidence gating | Low-score memories withheld, flagged in dashboard |
| Memory injected in wrong prompt position | No model-aware prompt building | Per-model-family templates in `nsn.context()` |

### What's Wrong with Existing Solutions (mem0, Zep, Letta)
- **mem0** — Black-box scoring, no observability, poor SLM fit, cloud-only, no confidence gating
- **Zep** — Chat history summarization only, no structured agent memory
- **Letta** — GPT-class focused, too heavy, complex self-hosting
- **LangChain Memory** — Stateless, no cross-session persistence
- **All of them** — No sleep-phase consolidation, no residual memory, no miss-rate metrics, no `pin()` primitive, no implicit feedback

---

## 3. Core Architecture — NeuroSleepNet

```
┌──────────────────────────────────────────────────────────────────┐
│                        Your SLM Agent                             │
│                    wrapped by nsn.wrap()                          │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                  NeuroSleepNet Intercept Layer
                    (hooks on structured I/O)
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                  NeuroSleepNet CORE ENGINE                         │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              LAYER 1 — TASK-AWARE ATTENTION                  │ │
│  │   Reads incoming query → scores all memories by relevance   │ │
│  │   Filters noise, surfaces task-specific context             │ │
│  │   Guides what gets replayed during sleep phase              │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │            LAYER 2 — RESIDUAL MEMORY PATHWAYS               │ │
│  │   Stable channels that NEVER overwrite old knowledge        │ │
│  │   New memories are added alongside, not on top of old ones  │ │
│  │   Gradient-safe: old tasks stay intact when learning new    │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │             LAYER 3 — SLEEP REPLAY ENGINE                   │ │
│  │   Runs during idle / scheduled windows ("offline sleep")    │ │
│  │   Replays high-value memories to reinforce them             │ │
│  │   Merges, deduplicates, and consolidates fragmented memory  │ │
│  │   Attention layer guides what gets replayed (not random)    │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────┐  ┌────────────┴──────┐  ┌───────────────────────┐ │
│  │  Vector  │  │  Structured Store  │  │   Telemetry Collector │ │
│  │  Store   │  │  (metadata, scope) │  │   (→ dashboard)       │ │
│  └──────────┘  └───────────────────┘  └───────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌──────────────────┐          ┌────────────────────────────┐
   │   Storage Layer  │          │  NeuroSleepNet Dashboard   │
   │  Qdrant/Chroma   │          │  Live memory metrics       │
   │  PostgreSQL      │          │  Sleep cycle viewer        │
   │  Redis           │          │  Attention heatmaps        │
   └──────────────────┘          └────────────────────────────┘
```

### The Sleep Cycle
```
AWAKE PHASE                         SLEEP PHASE
(agent is running)                  (idle / scheduled)

  New experience                    Sleep Engine triggers
       │                                    │
  Attention scores it                Attention selects
  → stored in short-term             high-value memories
    episodic buffer                         │
                                    Residual pathways
                                    reinforce them into
                                    long-term semantic store
                                           │
                                    Dedup + merge similar
                                    memories → consolidation
                                           │
                                    WAKE PHASE: agent is
                                    smarter than before sleep
```

---

## 4. The SDK — Full API Surface

### Install
```bash
pip install neurosleepnet
# Installs the neurosleepnet package + the nsn/ alias
# Both import nsn and import neurosleepnet resolve to the same library
```

### Core 3-Line Integration
```python
import nsn

nsn.init(project="my-coding-assistant")
# [NeuroSleepNet] Project initialized → Dashboard: http://localhost:3000/p/xk9p2q

agent = nsn.wrap(your_slm_function)
# agent now has full NeuroSleepNet memory. Call it exactly like before.
response = agent("What did we discuss last time?")
```

---

### Full SDK Function Reference

#### Initialization & Setup
```python
nsn.init(
    project="my-agent",           # Required: project name / namespace

    # --- Deployment mode ---
    mode="local",                  # "local"     → SQLite + Chroma, zero Docker (default)
                                   # "self-host" → connects to your running Docker stack

    # --- Self-host only ---
    host="http://localhost:8080",  # URL of your Docker entrypoint (API)
    api_key="nsn_...",            # Your self-generated secret key.
                                   # Set in Docker .env on first deploy.
                                   # The SDK sends this on every request so only
                                   # your own code can read/write memories.
                                   # You generate it — nobody issues it to you.
                                   # Not needed in local mode (no server, no auth surface).

    # --- Memory behaviour ---
    memory_window=4096,           # Max tokens to inject into SLM context
    sleep_interval=300,           # Seconds between auto sleep cycles (default: 5 min)
    sleep_on_exit=True,           # Run consolidation when process exits cleanly
                                   # Critical for short-lived scripts / CLIs
    embed_model="local",          # "local" | "openai" | "cohere"
    recall_threshold=0.6,         # Memories below this score are withheld
                                   # and flagged in dashboard as misses
    implicit_feedback=True,       # Watch follow-up turns for behavioral feedback signal
    decay=True,                   # Enable memory decay for stale entries
    debug=False                   # Verbose logging
)
```

> **Default is `mode="local"`** — SQLite + Chroma, runs fully in-process, zero external dependencies. No Docker, no API key. Graduate to `"self-host"` when you need multi-user or a persistent full-stack deployment.

> **Generating your self-host API key:** On first Docker deploy, run `docker compose run api python -m neurosleepnet.keygen` — prints the key once, writes the hash to Postgres. Set it in your app as `NSN_API_KEY=nsn_...` and pass it via `api_key=os.environ["NSN_API_KEY"]`. Rotate with the same command — old key invalidated immediately.

#### Agent Wrapping
```python
# Wrap any callable LLM/SLM
# nsn.wrap() hooks on structured I/O — it does NOT monkey-patch your function.
# Streaming, tool calls, system prompts, retry logic all pass through untouched.
agent = nsn.wrap(
    fn=your_llm_fn,              # Any function: fn(prompt) -> str
                                  # or fn(messages=[...]) -> str  (chat format)
    user_id="u_123",             # Optional: scope memory to a user
    agent_id="support-bot",      # Optional: scope memory to an agent role
    memory_types=["episodic", "semantic", "procedural"],
    streaming=False,             # Set True if fn() yields tokens (streaming)
)

# Use exactly like before — NeuroSleepNet is invisible
response = agent("Summarize what you know about me")
```

> **Important:** `nsn.wrap()` reads the structured input and output at the boundary — it never intercepts mid-stream tokens or tool execution. If your agent has complex internals (tool loops, retries, multi-turn), use `nsn.remember()` and `nsn.recall()` directly at the points you control rather than wrapping the outer function.

#### Direct Memory Operations
```python
# Add a memory manually
nsn.remember(
    content="User prefers Python 3.11+ and hates f-string nesting",
    user_id="u_123",
    type="semantic",             # episodic | semantic | procedural | user
    importance=0.9               # Optional: 0.0–1.0 override
)

# Recall memories relevant to a query
memories = nsn.recall(
    query="what coding style does this user prefer?",
    user_id="u_123",
    top_k=5,                     # Number of memories to return
    memory_types=["semantic"]    # Filter by type
)
# Returns: List[Memory] with .content, .score, .id, .age, .type

# Forget a specific memory
nsn.forget(memory_id="mem_abc123")

# Forget everything for a user (GDPR, right-to-erasure)
nsn.forget_user(user_id="u_123")

# Forget entire project
nsn.forget_project(project="old-project")

# Pin a memory — permanent, immutable, always injected first, never decayed
# Use for hard rules that must never be forgotten or overwritten
nsn.pin(
    content="This agent is deployed in a legal context. Never give direct legal advice.",
    user_id=None,                # None = applies to all users in this project
    label="legal-disclaimer"     # Optional: human-readable tag for dashboard
)

nsn.pin(
    content="User is a senior cardiologist. Always use clinical terminology.",
    user_id="u_123",
    label="user-persona"
)

# List all pinned memories
nsn.list_pins(user_id="u_123")

# Remove a pin (requires explicit confirmation — pins are hard to delete by design)
nsn.unpin(memory_id="mem_abc123", confirm=True)
```

#### Feedback & Reinforcement
```python
# --- Explicit feedback (manual) ---
# Tell NeuroSleepNet if a recalled memory was helpful
nsn.feedback(
    memory_id="mem_abc123",
    helpful=True,                # True = reinforce, False = downweight
    context="user confirmed it"
)

nsn.feedback_batch([
    {"memory_id": "mem_001", "helpful": True},
    {"memory_id": "mem_002", "helpful": False},
])

# --- Implicit feedback (behavioral — recommended for nsn.wrap() users) ---
# NeuroSleepNet watches what happens AFTER a recall. You don't need to know
# which memory was used — it figures it out from the next user turn.
#
# Positive signal (user builds on the answer, continues naturally):
#   → recalled memories get upweighted automatically
#
# Negative signal (user corrects the agent, contradicts, or asks again):
#   → recalled memories get downweighted automatically
#
# Enable in nsn.init():
nsn.init(
    project="my-agent",
    implicit_feedback=True       # Default: True when using nsn.wrap()
)
```

> **Recommendation:** Use implicit feedback as the primary signal. Explicit `nsn.feedback()` is best for batch pipelines and eval harnesses where you control the scoring, not for live agent code where you'd have to manually wire it everywhere.
```

#### Sleep Control
```python
# Manually trigger a sleep cycle (consolidation + dedup)
nsn.sleep(project="my-agent")

# Check sleep cycle status
status = nsn.sleep_status()
# Returns: last_sleep, next_sleep, memories_consolidated, dupes_removed

# Pause / resume automatic sleep
nsn.sleep_pause()
nsn.sleep_resume()
```

#### Inspection & Debugging
```python
# List all memories for a user
mems = nsn.list_memories(user_id="u_123", limit=50)

# Search memories by content
results = nsn.search(query="Python", user_id="u_123")

# Get memory stats for a project
stats = nsn.stats()
# Returns: total_memories, by_type, avg_recall_score,
#          token_savings, sleep_cycles_run, memories_consolidated

# Export all memories (backup / portability)
nsn.export(path="./backup.json")

# Import memories from backup
nsn.import_memories(path="./backup.json")

# Open dashboard in browser
nsn.dashboard()
```

#### Context Building (Advanced)
```python
# Build a memory context string ready to inject into a prompt.
# NeuroSleepNet knows where small models pay attention — context is positioned
# and formatted per model family, not just appended to the start.
context = nsn.context(
    query="help user debug their code",
    user_id="u_123",
    max_tokens=512,
    model_family="phi3",         # "phi3" | "mistral" | "gemma" | "llama3"
                                  # | "generic" (default)
                                  # Adjusts injection position + format
                                  # to match each model's known attention pattern
    format="xml",                # "xml" | "markdown" | "plain"
    include_pins=True,           # Always inject pinned memories (default: True)
    min_score=0.6                # Override global recall_threshold for this call
)

prompt = f"{context}\n\nUser: {user_message}"
response = your_slm(prompt)
```

> **Why this matters for SLMs:** A 4K-context model loses information buried in the middle of the prompt. `model_family` tells NeuroSleepNet where to place memory context so the model actually uses it — Phi-3 and Mistral have meaningfully different attention patterns at small context sizes. No other memory library does this.

---

## 5. Dashboard — Live Observability

### First-Run Output
```
$ python agent.py

[NeuroSleepNet] Initializing project: my-coding-assistant
[NeuroSleepNet] Mode: local (SQLite + Chroma, in-process)
[NeuroSleepNet] Sleep Engine: active (cycle: 5 min, sleep_on_exit: enabled)
[NeuroSleepNet] Embed model: local (sentence-transformers/all-MiniLM-L6-v2)
[NeuroSleepNet] ─────────────────────────────────────────────
[NeuroSleepNet] Dashboard live → http://localhost:3000/p/xk9p2q
[NeuroSleepNet] ─────────────────────────────────────────────
[NeuroSleepNet] Ready. 0 memories | 0 users | 0 sleep cycles
```

### Dashboard Panels

| Panel | Description |
|---|---|
| **Memory Health Score** | Composite: freshness × recall accuracy × dedup ratio |
| **Sleep Cycle Log** | Timeline of every sleep phase — consolidated, pruned |
| **Attention Heatmap** | Which memory types recalled most per task/user |
| **Recall Hit Rate** | % of recall attempts that met the confidence threshold |
| **Recall Miss Rate** | % withheld due to low confidence — shown alongside hits, not hidden |
| **Miss Inspector** | Browse every withheld memory: query, score, reason — for debugging retrieval gaps |
| **Implicit Feedback Stream** | Real-time signal: positive/negative behavioral signals per session |
| **Residual Pathway Map** | Visual graph of memory connections across tasks |
| **Token Savings Meter** | Tokens saved vs. always stuffing full history |
| **Live Session Feed** | Real-time stream of agent interactions + memory events |
| **Decay Queue** | Memories fading — scheduled for sleep pruning |
| **Pin Manager** | View, edit, and remove pinned memories per project / user |
| **User Memory Explorer** | Browse any user's memory profile, edit or delete |
| **Anomaly Alerts** | Spikes in miss rate, retrieval failures, dedup anomalies |

> **Miss rate is a first-class metric.** Knowing what NeuroSleepNet *didn't* inject is as important as knowing what it did. A rising miss rate is an early signal that your memory store has drifted, your recall threshold is too aggressive, or your embeddings need retuning.

---

## 6. Two Deployment Options

NeuroSleepNet has exactly two deployment paths. Pick one based on your needs. Both use the same `import nsn` SDK surface — the code you write is identical.

---

### Option A — Import Mode (default, zero infrastructure)

```bash
pip install neurosleepnet
```

```python
import nsn

nsn.init(project="my-agent")
# That's it. No Docker. No config. No external services.
```

**How it works under the hood:**
- Storage: SQLite (structured) + Chroma (vector) — both run fully in-process
- Sleep engine: background thread inside the Python process
- `sleep_on_exit=True` by default — consolidation fires when the process exits cleanly, even for scripts that run for 30 seconds
- Embeddings: `sentence-transformers` running locally, zero network calls
- Dashboard: lightweight local web server spun up on first `nsn.init()`, accessible at `http://localhost:3000/p/<project_id>`

**When to use this:**
- Building and testing agents locally
- Single-developer projects
- CLI tools, notebooks, scripts
- Anywhere Docker is unavailable or overkill
- Privacy-critical environments where you need certainty that nothing leaves the machine

**What you give up:**
- No multi-process memory sharing (memory is scoped to the process)
- No persistent dashboard beyond the local server
- Sleep engine is a thread, not a dedicated worker — heavy consolidation runs synchronously on exit

**Package structure:**
```
pip install neurosleepnet     # installs the neurosleepnet package
                               # also installs the nsn/ re-export alias
import nsn                    # works  ✅
import neurosleepnet          # also works  ✅
```

The `nsn/` directory is a thin wrapper inside the SDK:
```python
# nsn/__init__.py
from neurosleepnet import *   # re-exports everything
```

---

### Option B — Docker Self-Host Mode (full production stack)

```bash
git clone https://github.com/neurosleepnet/neurosleepnet
cd neurosleepnet
docker compose up -d
```

```python
import nsn

nsn.init(
    project="my-agent",
    mode="self-host",
    host="http://localhost:8080"
)
# SDK points to the local Docker stack. Same API, full power.
```

**What spins up:**
```
neurosleepnet-proxy      → :8080   Unified API & Dashboard (via Nginx)
neurosleepnet-api        → :8000   FastAPI core (internal)
neurosleepnet-dashboard  → :8080   Next.js dashboard (via proxy)
neurosleepnet-qdrant     → :6333   Qdrant vector store
neurosleepnet-postgres   → :5432   PostgreSQL (metadata, feedback, scopes, miss log)
neurosleepnet-redis      → :6379   Cache + sleep job queue + rate limiting
neurosleepnet-worker     →  —      Celery sleep engine (full async consolidation)
```

**How it works under the hood:**
- Storage: Qdrant (vector) + PostgreSQL (structured) — persistent across restarts
- Sleep engine: dedicated Celery worker with Redis queue — fully async, never blocks the API
- Dashboard: full Next.js app at `localhost:8080` — all 14 panels live
- All data stays on your machine — no external network calls unless you configure optional cloud embeddings
- API key authentication on all endpoints via Caddy reverse proxy (TLS enforced)

**When to use this:**
- Multi-user agents (multiple `user_id`s writing/reading concurrently)
- Production deployments on your own server or private cloud
- Teams where multiple processes or services share the same memory store
- When you need the full dashboard with the residual pathway map, miss inspector, and pin manager

**What you give up:**
- Requires Docker and ~5 minutes of setup
- More moving parts to maintain

**Teardown:**
```bash
docker compose down           # stop services
docker compose down -v        # stop + wipe all data (irreversible)
```

---

### Side-by-Side Comparison

| | **Import Mode** | **Docker Self-Host** |
|---|---|---|
| Setup | `pip install` | `docker compose up -d` |
| Infrastructure | None | 6 Docker services |
| Storage | SQLite + Chroma | Qdrant + PostgreSQL |
| Sleep engine | In-process thread | Dedicated Celery worker |
| Dashboard | Local server (:3000) | Full Next.js (:3000) |
| All 14 dashboard panels | Subset (local panels) | ✅ Full |
| Multi-process memory sharing | ❌ | ✅ |
| Data leaves machine | ❌ | ❌ |
| `sleep_on_exit` | ✅ | ✅ |
| Auth / TLS | Not needed | ✅ via Caddy |
| Ideal for | Dev, scripts, solo agents | Production, teams, multi-user |
| Cost | Free | Free |

> **The SDK API is identical in both modes.** Switching from Import Mode to Docker Self-Host is a one-line change in `nsn.init()` — no other code changes required.

---

## 7. Memory Types (NeuroSleepNet Model)

| Type | Biological Analog | What NeuroSleepNet Stores | Example |
|---|---|---|---|
| **Episodic** | Hippocampus (events) | Session events, exchanges | "User asked about async bugs on Apr 20" |
| **Semantic** | Neocortex (facts) | Long-term facts, preferences | "User is a senior dev, prefers Python" |
| **Procedural** | Cerebellum (skills) | How-to patterns agent learned | "Always ask scope before writing code" |
| **User-scoped** | Personal identity | Per-user isolated profile | Isolated per `user_id` |
| **Agent-scoped** | Shared team knowledge | Cross-user domain knowledge | Shared pool for all users |

Sleep cycles **promote** memory up the chain — episodic events become semantic facts over time, exactly like the human brain. Episodic memories accessed 3+ times are automatically promoted to semantic type during the next sleep cycle.

---

## 8. Technical Stack

The stack has two configurations — one per deployment option. The SDK is the same in both.

### Import Mode Stack
| Component | Technology | Notes |
|---|---|---|
| **SDK** | Python 3.9+ (`neurosleepnet` + `nsn` alias) | Core deps: `httpx`, `pydantic` |
| **Vector Store** | Chroma (in-process) | No server needed, embedded |
| **Structured Store** | SQLite (in-process) | Single file, portable |
| **Sleep Engine** | Background thread + `atexit` | Runs inside the Python process |
| **Embeddings** | `sentence-transformers` (local) | `all-MiniLM-L6-v2` default |
| **Dashboard** | Lightweight local HTTP server | Spun up by `nsn.init()`, no install |

### Docker Self-Host Stack
| Component | Technology | Notes |
|---|---|---|
| **API** | FastAPI (async, OpenAPI docs) | All endpoints, versioned at `/api/v1/` |
| **Vector Store** | Qdrant | Persistent, high-performance ANN search |
| **Structured Store** | PostgreSQL | Memory metadata, feedback, miss log, scopes |
| **Cache** | Redis | Hot memories, session state, rate limiting |
| **Sleep Engine** | Celery + Redis | Fully async worker, never blocks API |
| **Embeddings** | `sentence-transformers` (local default) | OpenAI / Cohere optional via config |
| **Attention Layer** | Cosine similarity + feedback re-ranking | Runs in API process |
| **Reverse Proxy** | Caddy | TLS termination, API key auth enforcement |
| **Dashboard** | Next.js 14 (App Router) | All 14 panels, WebSocket live feed |
| **Graphs** | D3.js | Residual pathway map, attention heatmap |
| **Charts** | Recharts | Metrics panels |

### SDK Package Structure
```
neurosleepnet/
├── __init__.py          # Full public API surface (all nsn.* functions)
├── local_store.py       # SQLite + Chroma storage (Import Mode)
├── local_sleep.py       # In-process sleep engine (Import Mode)
├── remote_client.py     # HTTP client → Docker API (Self-Host Mode)
├── context.py           # nsn.context() with model-family templates
├── feedback.py          # Implicit + explicit feedback engine
├── embed.py             # Embedding fallback chain
└── dashboard.py         # Local dashboard server launcher

nsn/
└── __init__.py          # from neurosleepnet import *  (alias only)
```

---

## 9. NeuroSleepNet vs Competitors

| | **NeuroSleepNet** | mem0 | Zep | Letta |
|---|---|---|---|---|
| SLM-optimized context window | ✅ | ❌ | ❌ | ❌ |
| Sleep-phase consolidation | ✅ | ❌ | ❌ | ❌ |
| Residual memory pathways | ✅ | ❌ | ❌ | ❌ |
| Task-aware attention retrieval | ✅ | Partial | ❌ | Partial |
| Live observability dashboard | ✅ | ❌ | ❌ | ❌ |
| Miss rate tracking | ✅ | ❌ | ❌ | ❌ |
| Confidence threshold gating | ✅ | ❌ | ❌ | ❌ |
| Permanent memory (`pin()`) | ✅ | ❌ | ❌ | ❌ |
| Implicit behavioral feedback | ✅ | ❌ | ❌ | ❌ |
| Per-model-family prompt placement | ✅ | ❌ | ❌ | ❌ |
| Zero-setup local mode (no Docker) | ✅ | ❌ | ❌ | ❌ |
| True self-hosting (1 command) | ✅ | ❌ | Partial | Complex |
| Catastrophic forgetting prevention | ✅ | ❌ | ❌ | Partial |
| 3-line integration | ✅ | ❌ | ❌ | ❌ |
| Memory export / import | ✅ | ❌ | ❌ | ❌ |

---

## 10. Build Checkpoints

Each checkpoint is a wall to break through — not a calendar milestone. Move to the next only when the current one is fully conquered.

---

### Checkpoint 1 — "It Works Locally, Zero Setup"
**The wall:** Can a developer `pip install nsn`, call `nsn.init()` + `nsn.wrap()`, and have their SLM actually remember something across two separate runs — with no Docker, no config file, nothing else installed?

- [ ] `nsn.init()` defaults to `mode="local"` — SQLite + Chroma, fully in-process
- [ ] First run prints dashboard link; subsequent runs are silent and fast
- [ ] `nsn.wrap(fn)` hooks on structured I/O without breaking streaming, tool calls, or system prompts
- [ ] `nsn.remember()` and `nsn.recall()` work end-to-end
- [ ] `nsn.pin()` stores a permanent memory — survives sleep cycles, decay, and dedup
- [ ] `nsn.forget()` and `nsn.forget_user()` work cleanly
- [ ] `sleep_on_exit=True` fires consolidation on clean process exit (covers scripts and CLIs)
- [ ] Basic `nsn.stats()` returns something meaningful

**You've beaten this when:** A developer installs NeuroSleepNet on a Friday evening, builds a simple Phi-3 coding assistant, kills the terminal, comes back Saturday morning, and the agent remembers everything from Friday — no setup beyond `pip install neurosleepnet`.

---

### Checkpoint 2 — "Sleep Actually Works"
**The wall:** The sleep engine runs, actually consolidates memories, and the agent is measurably better after it than before — for both long-running servers AND short-lived scripts.

- [ ] In-process sleep thread for local mode; Celery + Redis worker for self-host
- [ ] `sleep_on_exit=True` fires a full consolidation when the Python process exits cleanly — covers notebooks, CLIs, one-shot scripts that never hit a scheduled interval
- [ ] Sleep cycle: episodic buffer → semantic long-term store (promotion pipeline)
- [ ] Deduplication: near-duplicate memories merged, not duplicated
- [ ] `nsn.sleep()` triggerable manually; `nsn.sleep_status()` returns accurate info
- [ ] `nsn.sleep_pause()` / `nsn.sleep_resume()` work
- [ ] Demonstrable: run agent for 10 turns, trigger sleep, run 10 more — recall is sharper

**You've beaten this when:** You can show a before/after recall accuracy improvement after a sleep cycle — and it works for both a long-running API server and a 30-second command-line script.

---

### Checkpoint 3 — "Dashboard Is Alive"
**The wall:** The first-run dashboard link opens to something genuinely useful — not a placeholder. A developer can look at it and immediately understand what their agent knows AND what it missed.

- [ ] First-run link auto-generates and opens (or prints) a live URL
- [ ] Memory count, type breakdown, health score rendering in real time
- [ ] Sleep cycle log shows last run, what was consolidated, what was pruned
- [ ] Live session feed: every `recall()`, `remember()`, and `pin()` event appears as it happens
- [ ] **Miss rate panel**: every withheld memory (below `recall_threshold`) is visible with its score and the query that triggered it — not hidden
- [ ] **Miss inspector**: developer can click any miss and see exactly why it was withheld
- [ ] **Pin manager**: view, edit, remove pinned memories per project and per user
- [ ] User memory explorer: browse and delete memories per user
- [ ] Anomaly alerts: miss rate spike, recall score drop, dedup failure

**You've beaten this when:** You demo NeuroSleepNet to someone new, they open the dashboard, and without any explanation they can tell you both what the agent remembers *and* what it failed to recall last session.

---

### Checkpoint 4 — "Docker Self-Host Works Out of the Box"
**The wall:** A developer who has never heard of NeuroSleepNet can run the full Docker stack — API, dashboard, Qdrant, PostgreSQL, Redis, sleep worker — in under 5 minutes with zero troubleshooting. AND switching from Import Mode to Self-Host is one line of code change.

- [ ] `docker compose up -d` spins up all 6 services cleanly on first attempt
- [ ] `nsn.init(mode="self-host", host="http://localhost:8080")` connects with zero additional config
- [ ] All 14 dashboard panels render at `localhost:8080` with real data
- [ ] No data leaves the machine — verified in network logs
- [ ] A developer migrating from Import Mode changes exactly one line in `nsn.init()` — no other code changes
- [ ] `docker compose down -v` cleanly wipes all data (documented, tested)
- [ ] README Docker section: someone with basic Docker knowledge follows it cold, zero questions

**You've beaten this when:** A privacy-conscious team (legal, medical, fintech) deploys the Docker stack on their own server in one afternoon and their Import Mode agent points to it without any other changes.

---

### Checkpoint 5 — "The Attention Layer Is Smarter Than Search"
**The wall:** NeuroSleepNet's task-aware attention retrieval must outperform naive vector search. Implicit behavioral feedback must visibly change what gets recalled without the developer wiring anything.

- [ ] Attention re-ranking layer live: feedback scores influence retrieval order
- [ ] **Implicit feedback working**: positive follow-up turns upweight recalled memories; corrections downweight them — no explicit `nsn.feedback()` call required
- [ ] Explicit `nsn.feedback(helpful=True/False)` still available for eval harnesses
- [ ] `nsn.feedback_batch()` works for bulk rating
- [ ] `recall_threshold` gating: memories below score are withheld and logged as misses
- [ ] Attention heatmap in dashboard shows which memory types are used most per task
- [ ] Residual pathway map rendered in dashboard (memory connection graph)
- [ ] Measurable: same query returns better top-3 after 20 implicit feedback signals vs. cold start

**You've beaten this when:** Implicit feedback alone — with zero explicit `nsn.feedback()` calls — produces measurable recall improvement over 50 sessions in an A/B test.

---

### Checkpoint 6 — "SLM Beats GPT-4 on a Real Task"
**The wall:** Publish a reproducible benchmark where a small open-source model + NeuroSleepNet outperforms GPT-4 on a specific domain task. The domain must be one where memory is the *decisive variable* — not model capability.

**Chosen domain: multi-session coding assistance.** This is the benchmark to run because:
- SLMs are embarrassingly bad at it *specifically because of memory*, not intelligence
- Developers immediately understand and care about it
- The gap between "raw SLM" and "SLM + NeuroSleepNet" is visually dramatic

- [ ] Build eval harness: 10 simulated users, 10 sessions each, consistent coding tasks
- [ ] Each session builds on previous ones (variable names, style preferences, past bugs, project conventions)
- [ ] Score on: consistency across sessions, correct recall of past context, no repetition of already-answered questions
- [ ] Run four conditions: raw Phi-3 · Phi-3 + NeuroSleepNet · GPT-4 (no memory) · GPT-4 + mem0
- [ ] `nsn.context()` with `model_family="phi3"` prompt placement proven to outperform generic injection
- [ ] Results written up, reproducible, published (blog post + GitHub)
- [ ] Community can replicate with one script: `python benchmark.py`

**You've beaten this when:** Someone tweets the benchmark and the reaction is "wait, Phi-3 beat GPT-4 at remembering my codebase?"

---

### Checkpoint 7 — "The Ecosystem Plugs In"
**The wall:** NeuroSleepNet works inside the tools developers already use — not as a replacement for their stack, but as an invisible layer underneath it.

- [ ] LangChain integration: `NeuroSleepNetMemory` drop-in memory class
- [ ] LlamaIndex integration: `NSNRetriever` wrapper
- [ ] Ollama native support: `nsn.wrap(ollama.chat)` works out of the box (Import Mode and Self-Host)
- [ ] LM Studio support
- [ ] TypeScript/Node.js SDK parity with Python SDK
- [ ] Each integration has a 5-line usage example in docs

**You've beaten this when:** A LangChain user adds NeuroSleepNet to an existing agent without rewriting anything.

---

### Checkpoint 8 — "Memory Becomes a Competitive Asset"
**The wall:** NeuroSleepNet memories are not just useful during inference — they become a reusable, transferable, improvable asset that compounds over time.

- [ ] `nsn.export()` / `nsn.import_memories()` fully working — portable memory files
- [ ] Edge deploy mode: SQLite + local embeddings, zero Docker (runs on a laptop or Pi)
- [ ] LoRA fine-tune pipeline: use consolidated NeuroSleepNet memories as fine-tuning data
- [ ] Multi-agent shared memory: two agents reading from the same memory pool
- [ ] GDPR toolkit: `nsn.forget_user()` is audit-logged and provably complete

**You've beaten this when:** A team exports their agent's 6-month memory, imports it into a new model, and the new model starts smart instead of blank.

---

## 11. Security & Fallback

These are not optional. Every checkpoint must be built with these in place from the start — they are not a final pass.

---

### Security

#### API & Authentication
- All Docker Self-Host API endpoints require a signed API key passed via `Authorization: Bearer nsn_...` header
- API keys are hashed at rest (bcrypt) — the raw key is shown only once at creation via `docker compose run api python -m neurosleepnet.keygen`
- Import Mode runs fully in-process with no network surface — no auth needed, no attack surface
- Rate limiting on all endpoints via Redis token bucket — configurable per project, per user
- All requests travel over HTTPS only; Docker Self-Host enforces TLS via bundled Caddy reverse proxy

#### Memory Data Isolation
- Every memory record is scoped to `(project_id, user_id)` at the database row level — cross-project and cross-user reads are impossible by schema design, not just by convention
- Pinned memories are write-protected at the API level — deletion requires `confirm=True` and is audit-logged
- `nsn.forget_user()` triggers a hard-delete cascade across vector store, structured store, and Redis cache — verified and audit-logged
- Self-host: all data stays on your machine. Embeddings are computed locally by default (`embed_model="local"`) — no memory content ever sent to a third party unless explicitly configured

#### Secrets & Config
- API keys, database credentials, and embed provider keys are loaded from environment variables only — never hardcoded, never logged
- The SDK never logs memory content at any log level — only memory IDs and scores appear in logs
- Dashboard access in Docker Self-Host mode is protected by session token (set in `.env` on deploy)
- Import Mode dashboard is local-only (`localhost`) — no session token needed

#### Dependency Hygiene
- Dependencies are pinned with exact versions in `pyproject.toml` and verified via hash in `requirements.lock`
- Automated dependency vulnerability scanning on every commit (Dependabot or equivalent)
- Minimal dependency surface in the SDK: only `httpx` and `pydantic` for core functionality

---

### Fallback Mechanisms

#### Storage Fallback
- **Import Mode:** If Chroma is unavailable, falls back to in-memory ephemeral store — agent runs, memory lasts for the session, clear warning surfaced
- **Docker Self-Host:** If Qdrant is unavailable, falls back to Chroma automatically and logs a warning — agent keeps running
- If Chroma is also unavailable (Self-Host), falls back to in-memory ephemeral store
- Storage degradation is always surfaced in the dashboard with the specific failure reason — never silent in either mode

#### Embedding Fallback
- If the configured embed model fails (API timeout, model load error), falls back to the next available option in order: `local → openai → cohere → tfidf`
- TF-IDF fallback ensures recall still works even with no embedding infrastructure — quality degrades gracefully, not catastrophically

#### Sleep Engine Fallback
- **Import Mode:** if the background thread crashes, sleep consolidation is re-attempted on next `nsn.init()` startup
- **Docker Self-Host:** if the Celery worker is unavailable, sleep cycles fall back to an in-process thread scheduler in the API container
- If `sleep_on_exit` fires but consolidation fails (e.g. storage error mid-cycle), a partial-state checkpoint is saved — next sleep resumes from the checkpoint, not from scratch
- Failed sleep cycles are logged to the dashboard with full error context, not silently dropped

#### Recall Fallback
- If recall returns zero results (empty store, all memories below threshold), the agent receives an explicit empty context — no hallucinated context, no silent failure
- If recall latency exceeds a configurable timeout (`recall_timeout_ms`, default 200ms), cached results from the last successful recall are returned with a staleness flag
- The dashboard tracks recall timeout rate as a metric — a rising timeout rate signals infrastructure issues before they impact users

#### Network & API Fallback (Docker Self-Host only)
- SDK implements automatic retry with exponential backoff (3 attempts, 100ms / 500ms / 2s) on transient network errors when `mode="self-host"`
- If the Docker API is unreachable after all retries, the SDK degrades to Import Mode automatically using the local SQLite snapshot — the agent keeps running
- Degradation is logged and surfaced to the developer with a clear message, never silently

#### Wrap Fallback
- If `nsn.wrap()` fails to extract memories from an exchange (malformed output, unexpected model response format), the original function output is returned unmodified — the agent is never broken by the memory layer
- Wrap errors are logged with the raw I/O that caused them, not swallowed

---

> **Principle:** NeuroSleepNet must never be the reason an agent goes down. Every failure mode has a defined degraded state that keeps the agent running. The developer is always informed — never left guessing.
>
> **Applies to both deployment options.** Import Mode has a simpler threat surface (no network, no auth needed) but all fallback mechanisms still apply. Docker Self-Host adds the full security layer on top.

---

## 12. Success Metrics

| Metric | What "Beaten" Looks Like |
|---|---|
| GitHub Stars | 3,000+ organic |
| PyPI installs/month | 15,000+ active installs |
| Active dashboard projects | 500+ live projects tracked |
| SLM+NeuroSleepNet vs GPT-4 benchmark | Published + community-replicated |
| Self-host deployments | 1,000+ verified Docker deployments |
| Local mode adoption | 60%+ of projects never leave `mode="local"` (simplicity working) |
| Recall hit rate (with feedback) | 80%+ of recalls meet threshold after 50 implicit signals |
| Miss rate trend | Miss rate decreasing week-over-week per project (feedback loop working) |
| Sleep consolidation ratio | 30%+ memory reduction per cycle (dedup working) |
| `nsn.pin()` usage | Present in 70%+ of production projects (the primitive is needed) |
| Fallback activations | Zero agent crashes attributable to NeuroSleepNet across all reported deployments |
| Security incidents | Zero cross-project or cross-user memory leaks |

---

## 13. Taglines

> *"Your SLM remembers. Your SLM learns. Your SLM wins."*

> *"NeuroSleepNet: The memory layer your SLM deserves."*

> *"Sleep-inspired memory. Production-grade results."*

---

*NeuroSleepNet — Because intelligence without memory is just a calculator.*