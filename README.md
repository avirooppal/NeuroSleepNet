# NeuroSleepNet

**Persistent memory for AI agents. Drop-in. Open-source. Local-first.**

> A 3B parameter model + NeuroSleepNet outperforms GPT-4o on domain-specific recall tasks.  
> [See benchmark →](#nsn-bench--benchmark-suite)

---

## Table of Contents

- [Quick Start](#quick-start)
- [Why NeuroSleepNet vs Mem0](#why-neurosleepnet-vs-mem0)
- [What's Included](#whats-included)
- [Framework Support](#framework-support)
- [Advanced API](#advanced-api)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Health Endpoints](#health-endpoints)
- [nsn-bench — Benchmark Suite](#nsn-bench--benchmark-suite)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Pricing](#pricing)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

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

**Self-hosted (full stack):**
```bash
git clone https://github.com/your-org/neurosleepnet
cd neurosleepnet
cp .env.example .env   # edit your keys
docker compose up
```

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
- **Offline cache** — local SQLite fallback when API is unreachable (SDK tries API directly first — SQLite is not a mandatory pipeline)
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
| LangGraph | Tier 3 | ⚠️ Experimental — wrap individual nodes only; graph-level wrapping unsupported and may produce undefined behavior |
| OpenAI SDK | — | ✅ Full (sync + streaming) |
| HuggingFace `pipeline` | — | ✅ Full (chat template injection) |
| Ollama | — | ✅ Full (generic callable) |
| Anthropic Claude | — | ✅ Full (sync + async) |

---

## Advanced API

### `nsn.init()`

```python
nsn.init(
    api_key="nsn_...",               # Required
    base_url="http://localhost:8080", # Optional: self-hosted endpoint (default: hosted API)
    project="my-agent-v2",           # Optional: namespace memories by project
    session_id=None,                  # Optional: override auto session ID
    fallback_mode="silent",           # "silent" | "warn" | "raise"
    max_context_tokens=2048,          # Cap injected memory size
    min_memories=3,                   # Always keep at least N memories
    offline_cache=True,               # SQLite fallback if API unreachable (SDK tries API first)
    log_level="info"                  # "debug" | "info" | "warn" | "none"
)
```

### Core Methods

```python
# Wrap any agent — all memory injection is transparent
agent = nsn.wrap(your_agent)

# Store a memory manually
nsn.remember(content="User prefers Python", importance=0.8, tags=["preference"])
# context keys: session_id (str), source ("user-input"|"tool-output"), agent_turn (int)
nsn.remember(content="Fixed auth bug", importance=0.9, context={"source": "tool-output"})

# Retrieve memories semantically — use nsn.recall(), not nsn.search()
results = nsn.recall(query="auth module fixes", top_k=5, min_score=0.7)
# min_score (float 0–1): filters out low-confidence memories post-retrieval

# Export / restore full memory state (snapshot/restore — not export_memory/import_memory)
snapshot = nsn.snapshot()
nsn.restore(snapshot)

# Diagnostics — prints formatted block to stdout AND returns the status object
status = nsn.status()
print(status.usage, status.latency, status.cache_hits)

# Explain last retrieval — why_retrieved breakdown for debugging
nsn.explain_last()

# Targeted pruning
nsn.forget(query="old context", older_than_days=30)

# Batch write (up to 100 memories) — REST: POST /v1/memories/batch
nsn.batch_remember([
    {"content": "fact1", "importance": 0.8},
    {"content": "fact2", "importance": 0.6},
])
```

### Framework-Specific Examples

**LangChain AgentExecutor (Tier 1):**
```python
from langchain.agents import AgentExecutor
import neurosleepnet as nsn

agent = AgentExecutor.from_agent_and_tools(...)
wrapped_agent = nsn.wrap(agent)
wrapped_agent.invoke({"input": "What did I ask before?"})
```

**OpenAI API:**
```python
from openai import OpenAI
import neurosleepnet as nsn

client = OpenAI(api_key="...")
wrapped_client = nsn.wrap(client)

response = wrapped_client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Remember this..."}]
)
```

**HuggingFace Pipeline:**
```python
from transformers import pipeline
import neurosleepnet as nsn

pipe = pipeline("text-generation", model="Qwen/Qwen2.5-0.5B")
wrapped_pipe = nsn.wrap(pipe)
result = wrapped_pipe("What do I prefer for coding?")
```

---

## Architecture

### Three Celery Queues (No Starvation)

The background task system uses three **separate** worker containers, each bound to a specific queue. A single merged worker causes sleep consolidation (long-running) to starve webhook delivery (time-sensitive).

```
┌─────────────┐   ┌──────────────────────┐   ┌─────────────────────────────────────┐
│  FastAPI    │──▶│  Redis Broker        │──▶│  worker-sleep    (-Q sleep,  c=2)   │
│  Backend    │   │                      │   │  worker-webhooks (-Q webhooks, c=3)  │
└─────────────┘   └──────────────────────┘   │  worker-embed    (-Q embed,  c=4)   │
                                             └─────────────────────────────────────┘
```

### Webhook Delivery: After-Commit Pattern

Webhook tasks are enqueued **after the database transaction commits**, never inside the FastAPI handler. This ensures any consumer receiving a `memory.stored` event can safely query the database and find the memory already persisted — no race conditions.

**Retry policy:** 3 attempts with exponential back-off (30s → 5m → 30m). Failed deliveries are logged with full payload for manual inspection.

**Why this matters:** Enqueuing inside the request handler (before commit) is the common mistake — if the DB write fails after the task is enqueued, the webhook fires for a memory that doesn't exist.

### SDK Fallback Cascade

The SDK tries the backend API directly. SQLite is a **fallback**, not an intermediate layer:

```
Normal:    SDK ──────────────────▶ FastAPI Backend
                                        │
Fallback:  SDK ──▶ SQLite Cache ───────▶ (syncs back when reconnected)
```

Full cascade:
1. **API healthy** → retrieve from backend, inject, log usage
2. **API slow (>500ms)** → use local SQLite cache, queue log for retry
3. **API unreachable** → skip injection, agent runs as-is, log warning
4. **SDK crash** → try/except catches all NSN code, original agent runs untouched

### Core Components

| Component | Path | Role |
|---|---|---|
| Python SDK | `sdk/python/neurosleepnet/` | Agent wrapping, adapters, SQLite fallback |
| FastAPI Backend | `backend/app/` | REST API, auth, rate limiting, webhooks |
| Embedding Service | `services/embed/` | Standalone FastEmbed — keeps API latency near zero |
| Celery Workers | `backend/app/workers/` | Sleep consolidation, webhook delivery, embed tasks |
| React Dashboard | `frontend/` | Memory Explorer, analytics, Sleep Engine controls |

---

## Project Structure

```
NeuroSleepNet/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── api/v1/                  # REST API endpoints
│   │   ├── core/                    # Core business logic
│   │   │   ├── attention.py         # Attention scoring
│   │   │   ├── consolidation.py     # Sleep phase logic
│   │   │   ├── sleep_engine.py      # Sleep consolidation engine
│   │   │   └── pii.py               # PII detection
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/                # Business logic services
│   │   ├── workers/                 # Celery task definitions
│   │   └── main.py                  # FastAPI app initialization
│   ├── alembic/                     # Database migrations
│   └── pyproject.toml
│
├── sdk/
│   ├── python/                      # Python SDK
│   │   ├── neurosleepnet/
│   │   │   ├── client.py            # API client
│   │   │   ├── cache.py             # SQLite offline cache
│   │   │   ├── wrappers.py          # Framework adapters
│   │   │   ├── benchmark/           # nsn-bench suite
│   │   │   └── __init__.py          # Public API surface
│   │   └── examples/
│   └── nodejs/                      # Node.js SDK
│
├── frontend/                         # React 18 / TypeScript / Vite dashboard
│   └── src/
│       ├── components/              # Landing page + UI components
│       ├── pages/                   # Dashboard pages
│       └── store/                   # Zustand state
│
├── services/
│   └── embed/                       # Standalone FastEmbed microservice
│
├── infra/
│   └── nginx/                       # Reverse proxy config
│
├── docs/                            # [coming soon]
│   ├── integration-guides.md
│   ├── api-reference.md
│   ├── error-reference.md
│   ├── self-hosted.md
│   └── pricing.md
│
├── docker-compose.yml               # Development stack (3 Celery worker services)
├── docker-compose.prod.yml          # Production stack
├── Makefile                         # Dev commands
└── pyproject.toml
```

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

# 5. Run frontend
cd frontend && npm run dev
```

> ⚠️ Do **not** run a single `celery worker` without `-Q` flags — it picks up all queues and recreates the starvation problem.

### Environment Variables

**Backend** (`backend/.env`):
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/neurosleepnet
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key-change-this
EMBEDDING_API_URL=http://localhost:8002
ENVIRONMENT=development
```

**Frontend** (`frontend/.env.local`):
```env
VITE_API_URL=http://localhost:8000
```

### Makefile Commands

```bash
make up        # Start all services
make down      # Stop services
make logs      # Tail logs
make test      # Run tests
make lint      # Run linters
make migrate   # Run Alembic migrations
make help      # All commands
```

---

## Health Endpoints

```
GET /health          → { status: "ok", db: "ok", redis: "ok", embed: "ok" }
GET /health/ready    → Kubernetes readiness probe
GET /health/deep     → Runs embed + DB write + retrieval, returns full latency breakdown
```

Use `/health/deep` for monitoring dashboards and the dashboard status panel. It is the endpoint that runs a full embed + DB write + retrieval round-trip and returns per-service latency stats.

---

## nsn-bench — Benchmark Suite

`nsn-bench` is a **separate open-source package** for memory quality benchmarking. It is distinct from load testing (API throughput — use `locust` for that).

```bash
pip install nsn-bench
nsn-bench run --model YOUR_MODEL --scenarios all

# Specific scenarios
nsn-bench run --scenarios "multi_turn_recall,cross_session"

# Generate shareable HTML report
nsn-bench report --output report.html
```

### Built-in Scenarios

| Scenario | Baseline | NSN Active | Δ |
|---|---|---|---|
| Multi-Turn Recall | 12% | 91% | **+79%** |
| Cross-Session Memory | 0% | 87% | **+87%** |
| Catastrophic Forgetting Resistance | 23% | 94% | **+71%** |
| **SLM Domain Q&A (Medical, 3B model)** | **18%** | **86%** | **+68%** |
| Attention Precision@5 | — | 89% | — |

Reports are shareable via public URL and embeddable as README badges: `![NSN Score](https://nsn.ai/badge/abc123)`

### Load Testing (Separate from nsn-bench)

```bash
pip install locust
cd backend
locust -f tests/load/locustfile.py -u 100 -r 10 -t 5m --headless
```

---

## Deployment

### Production Stack

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Production Environment

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:secure-pass@prod-db/neurosleepnet
REDIS_URL=redis://prod-redis:6379
JWT_SECRET=change-to-secure-random-value
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=info
```

### Services

| Service | Port | Role |
|---|---|---|
| `api` | 8000 | FastAPI backend |
| `nsn-embed` | 8002 | Embedding microservice |
| `worker-sleep` | — | Sleep consolidation queue |
| `worker-webhooks` | — | Webhook delivery queue |
| `worker-embed` | — | Async embedding queue |
| `db` | 5433 | PostgreSQL + pgvector |
| `redis` | 6380 | Celery broker + cache |
| `nginx` | 8080 | Reverse proxy |

---

## Troubleshooting

**API returns 503 on `/v1/memories`**
```bash
docker compose logs api             # Check FastAPI startup
docker compose logs db              # Check pgvector migration
docker compose exec db pg_isready   # Confirm DB is healthy
```

**Webhook events not firing**
```bash
docker compose logs worker-webhooks   # Check -Q webhooks worker is running
# Ensure you are running worker-webhooks, not a merged single worker without -Q flags
```

**Embeddings timing out**
```bash
docker compose logs nsn-embed         # Check embed service model download
docker compose logs worker-embed      # Check -Q embed worker backlog
```

**Memory retrieval feels stale**
```bash
# In Python:
nsn.status()        # Prints cache hits vs live API ratio to stdout
nsn.explain_last()  # Shows why_retrieved breakdown for last retrieval

# Via HTTP:
curl http://localhost:8000/health/deep  # Full latency breakdown: embed + DB + retrieval
```

**Celery workers not processing tasks**
```bash
docker compose logs worker-sleep      # Check sleep queue
docker compose logs worker-webhooks   # Check webhook queue
docker compose logs worker-embed      # Check embed queue

# Check Redis broker
docker compose exec redis redis-cli KEYS "celery*"
```

**Frontend won't load**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install && npm run dev
```

---

## Pricing

| Free | Pro | Enterprise |
|---|---|---|
| 10,000 memories, 1 project | 500,000 memories, unlimited projects | Unlimited |
| **Free forever** | **$29/mo** | **Contact us** |

No credit card required for Free. Self-hosted is **always free**.

---

## Contributing

### Code Style

- **Python**: PEP 8, formatted with Black + isort
- **TypeScript/React**: ESLint + Prettier (config included)
- **Git commits**: Conventional commits (`feat:`, `fix:`, `docs:`, etc.)

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Run `make test` and `make lint` locally
5. Commit with conventional commit messages
6. Open a Pull Request with a clear description

### Reporting Issues

Use GitHub Issues with:
- Clear title and reproduction steps
- Expected vs actual behavior
- Environment details (OS, Python version, Docker version)
- Relevant logs or error messages

---

## License

Apache 2.0. `nsn-bench` is a separate open-source package under the same license.
