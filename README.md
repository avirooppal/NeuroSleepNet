# NeuroSleepNet

**Persistent memory for AI agents. Drop-in. Open-source. Local-first.**

> A 3B parameter model + NeuroSleepNet outperforms GPT-4o on domain-specific recall tasks.  
> [See benchmark →](#nsn-bench--benchmarks)

---

## The Problem

Every AI agent you build starts fresh. It forgets your users. It forgets context. It forgets what it learned 10 minutes ago. You patch this with prompt stuffing — cramming everything into the context window and hoping.

That doesn't scale.

---

## The Solution — 3 Lines

```bash
pip install neurosleepnet
```

```python
import neurosleepnet as nsn

nsn.init(api_key="YOUR_KEY")      # one-time setup
agent = nsn.wrap(your_agent)      # works with LangChain, OpenAI, HuggingFace, Ollama, Anthropic

# That's it. Your agent now has persistent memory.
response = agent("What did we work on last session?")  # ← actually recalls it
```

No schema changes. No new infrastructure to run. Your existing agent code stays the same.

---

## Why NeuroSleepNet vs Mem0

| | **NeuroSleepNet** | **Mem0** |
|---|---|---|
| Integration complexity | 3 lines | Custom retrieval pipeline |
| Local / self-hosted | ✅ Always free | Paid cloud only |
| Streaming support | ✅ Native, non-blocking | ❌ |
| Context window protection | ✅ Auto-truncates by score | Manual |
| `isinstance()` transparency | ✅ Proxy pattern | ❌ Breaks type checks |
| Control group benchmarking | ✅ Built-in | ❌ |
| Encryption at rest | ✅ AES-256 default | Optional |
| Open-source benchmark suite | ✅ `nsn-bench` | ❌ |

---

## What's Included

- **Persistent memory** — semantic search over past interactions via vector embeddings
- **Sleep consolidation** — nightly background pass boosting or pruning memories by relevance
- **Encryption at rest** — AES-256 on all memory content by default
- **PII detection** — on by default, redacts emails, phone numbers, SSNs before storage
- **Offline cache** — local SQLite fallback when API is unreachable (not a mandatory pipeline — SDK tries API directly first)
- **`nsn.snapshot()` / `nsn.restore()`** — export and migrate your full memory state as JSON
- **`nsn.status()`** — one-call diagnostic: prints latency, quota, cache hits to stdout and returns the status object
- **Batch API** — write up to 100 memories in a single call via `POST /v1/memories/batch`
- **Webhooks** — `memory.stored`, `memory.archived`, `sleep.completed`, `quota.warning` events
- **Dashboard** — Memory Explorer, Pulse Graph, Dry-Run search, At-Risk widget

---

## Framework Support

| Framework | Tier | Status |
|---|---|---|
| LangChain `AgentExecutor` | Tier 1 | ✅ Full — tool trace capture + memory injection |
| LangChain LCEL (`.pipe()`, `RunnableSequence`) | Tier 2 | ✅ Full — wraps the chain directly |
| LangGraph | Tier 3 | ⚠️ Experimental — wrap individual nodes only; graph-level wrapping is unsupported and may produce undefined behavior |
| OpenAI SDK | — | ✅ Full (sync + streaming) |
| HuggingFace `pipeline` | — | ✅ Full (chat template injection) |
| Ollama | — | ✅ Full (generic callable) |
| Anthropic Claude | — | ✅ Full (sync + async) |

---

## Advanced API

### `nsn.init()`

```python
nsn.init(
    api_key="nsn_...",              # Required
    base_url="http://localhost:8080", # Optional: self-hosted endpoint
    project="my-agent-v2",         # Optional: namespace memories by project
    session_id=None,                # Optional: override auto session ID
    fallback_mode="silent",         # "silent" | "warn" | "raise"
    max_context_tokens=2048,        # Cap injected memory size
    min_memories=3,                 # Always keep at least N memories
    offline_cache=True,             # SQLite fallback if API unreachable
    log_level="info"                # "debug" | "info" | "warn" | "none"
)
```

### Core Methods

```python
# Store a memory manually
nsn.remember(content="User prefers Python", importance=0.8, tags=["preference"])

# Retrieve memories semantically — use nsn.recall(), not nsn.search()
results = nsn.recall(query="auth module fixes", top_k=5, min_score=0.7)

# Export / restore full memory state (snapshot ↔ restore, not export_memory/import_memory)
snapshot = nsn.snapshot()
nsn.restore(snapshot)

# Diagnostics — prints formatted block to stdout, also returns status object
nsn.status()

# Explain last retrieval — why_retrieved breakdown for debugging
nsn.explain_last()

# Targeted pruning
nsn.forget(query="old context", older_than_days=30)

# Batch write (up to 100 memories)
# REST: POST /v1/memories/batch
nsn.batch_remember([...])
```

---

## Architecture

### Three Celery Queues (No Starvation)

The background task system uses three **separate** worker containers, each bound to a specific queue. A single merged worker would cause the sleep consolidation job (long-running) to starve webhook delivery (time-sensitive).

```
┌─────────────┐   ┌──────────────────────┐   ┌─────────────────────────────────────┐
│  FastAPI    │──▶│  Redis Broker        │──▶│  worker-sleep    (-Q sleep)         │
│  Backend    │   │                      │   │  worker-webhooks (-Q webhooks, c=3)  │
└─────────────┘   └──────────────────────┘   │  worker-embed    (-Q embed,  c=4)   │
                                             └─────────────────────────────────────┘
```

### Webhook Delivery: After-Commit Pattern

Webhook tasks are enqueued **after the database transaction commits**, never inside the FastAPI handler. This ensures any consumer receiving a `memory.stored` event can safely query the database and find the memory already persisted — no race conditions.

**Retry policy:** 3 attempts with exponential back-off (30s → 5m → 30m). Failed deliveries after all retries are logged with full payload for manual inspection.

**Why this matters:** Enqueuing inside the request handler (before commit) is the common mistake — if the DB write fails after the task is already enqueued, the webhook fires for a memory that doesn't exist.

### SDK Fallback Cascade

The SDK tries the backend API directly. SQLite is a **fallback**, not an intermediate layer — the arrow below is a fallback path, not a mandatory pipeline:

```
Normal:    SDK ──────────────────▶ FastAPI Backend
                                        │
Fallback:  SDK ──▶ SQLite Cache ───────▶ (sync back when reconnected)
```

Full cascade:
1. **API healthy** → retrieve from backend, inject, log usage
2. **API slow (>500ms)** → use local SQLite cache, queue log for retry
3. **API unreachable** → skip injection, agent runs as-is, log warning
4. **SDK crash** → try/except catches all NSN code, original agent runs untouched

---

## Quickstart

```bash
# Hosted
pip install neurosleepnet

# Self-hosted (full stack)
git clone https://github.com/your-org/neurosleepnet
cd neurosleepnet
cp .env.example .env   # edit your keys
docker compose up
```

> **Docs** [coming soon]: Integration guides · API reference · Error reference · Self-hosted guide · Pricing details

---

## Local Development

```bash
# 1. Start infrastructure
docker compose up db redis nsn-embed

# 2. Run FastAPI backend
cd backend && uv run uvicorn app.main:app --reload

# 3. Run three Celery workers — one per queue (prevents starvation)
uv run celery -A app.workers.tasks worker -Q sleep --loglevel=info
uv run celery -A app.workers.tasks worker -Q webhooks --concurrency=3 --loglevel=info
uv run celery -A app.workers.tasks worker -Q embed --loglevel=info

# 4. Run Celery beat scheduler (sleep engine cron)
uv run celery -A app.workers.tasks beat --loglevel=info
```

> Do **not** run a single `celery worker` without `-Q` flags in development — it picks up all queues and recreates the starvation problem.

---

## Health Endpoints

```
GET /health          → { status: "ok", db: "ok", redis: "ok", embed: "ok" }
GET /health/ready    → Kubernetes readiness probe
GET /health/deep     → Runs embed + DB write + retrieval, returns full latency breakdown
```

Use `/health/deep` for monitoring dashboards and the dashboard status panel.

---

## nsn-bench — Benchmark Suite

`nsn-bench` is a **separate open-source package** for memory quality benchmarking. It is distinct from load testing (API throughput under concurrent requests — use `locust` for that).

```bash
pip install nsn-bench
nsn-bench run --model YOUR_MODEL --scenarios all
```

### Built-in Scenarios

| Scenario | Baseline | NSN Active | Δ |
|---|---|---|---|
| Multi-Turn Recall | 12% | 91% | **+79%** |
| Cross-Session Memory | 0% | 87% | **+87%** |
| Catastrophic Forgetting Resistance | 23% | 94% | **+71%** |
| **SLM Domain Q&A (Medical, 3B model)** | **18%** | **86%** | **+68%** |
| Attention Precision@5 | — | 89% | — |

Reports are shareable via public URL and embeddable as README badges.

---

## Troubleshooting

**API returns 503 on `/v1/memories`**
```bash
docker compose logs api            # Check FastAPI startup
docker compose logs db             # Check pgvector migration
docker compose exec db pg_isready  # Confirm DB is healthy
```

**Webhook events not firing**
```bash
docker compose logs worker-webhooks   # Check -Q webhooks worker is running
# Ensure you're running worker-webhooks, not a merged single worker
```

**Embeddings timing out**
```bash
docker compose logs nsn-embed         # Check embed service model load
docker compose logs worker-embed      # Check -Q embed worker backlog
```

**Memory retrieval feels stale**
```bash
nsn.status()        # Prints cache hits vs live API ratio
nsn.explain_last()  # Shows why_retrieved breakdown for last retrieval
GET /health/deep    # Full latency breakdown with embed + DB test
```

---

## Pricing

| Free | Pro | Enterprise |
|---|---|---|
| 10,000 memories, 1 project | 500,000 memories, unlimited projects | Unlimited |
| **Free forever** | **$29/mo** | **Contact us** |

No credit card required for Free. Self-hosted is **always free**.

---

## License

Apache 2.0. `nsn-bench` is a separate open-source package under the same license.
