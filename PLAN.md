# NeuroSleepNet — Full Product Build Plan
> A Sleep-Inspired Hybrid Memory Layer for Continual AI Learning

---

## ⚠️ FIRST ACTION: CLEANUP INSTRUCTIONS

> **AI Agent Instruction:** Before implementing anything, run the following to wipe the existing project state:

```bash
# Step 0 — Nuke existing structure
rm -rf backend/ frontend/src/old-* docker-compose.yml .env *.lock
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete

# Then scaffold fresh using uv (NOT pip/poetry)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv init neurosleepnet-backend
cd neurosleepnet-backend
```

> The frontend is pre-built. Only plug-in the backend + SDK.

---

## Table of Contents

1. [Product Vision & Pain Point Analysis](#1-product-vision--pain-point-analysis)
2. [Architecture Overview](#2-architecture-overview)
3. [Core NeuroSleepNet Concepts (Enhanced)](#3-core-neurosleepnet-concepts-enhanced)
4. [Pricing Plans](#4-pricing-plans)
5. [Folder Structure](#5-folder-structure)
6. [Tech Stack](#6-tech-stack)
7. [Database Schema](#7-database-schema)
8. [API Design](#8-api-design)
9. [Dashboard Design](#9-dashboard-design)
10. [Payment Integration (Razorpay)](#10-payment-integration-razorpay)
11. [Fallback & Safety Mechanisms](#11-fallback--safety-mechanisms)
12. [Docker & Deployment](#12-docker--deployment)
13. [Implementation Checkpoints](#13-implementation-checkpoints)

---

## 1. Product Vision & Pain Point Analysis

### What NeuroSleepNet Is

NeuroSleepNet is a **drop-in memory layer API** for AI applications. Instead of your AI starting fresh every conversation, NeuroSleepNet gives it persistent, evolving, and intelligent memory — inspired by how the human brain consolidates knowledge during sleep.

### Pain Points of Existing Solutions (mem0, Zep, etc.)

| Pain Point | mem0 / Zep | NeuroSleepNet Solution |
|---|---|---|
| **Catastrophic forgetting** | No native anti-forgetting mechanism | Sleep-phase replay consolidates old memories |
| **Flat memory** | All memories treated equally | Attention-weighted priority — important memories surface first |
| **No task context** | Global memory pool only | Task-aware namespacing + attention per task |
| **Expensive free tier** | Limited to 50-100 ops/month | 10,000 memory ops/month free |
| **No Indian payment support** | USD/card only | Razorpay (UPI, NetBanking, Cards, EMI) |
| **Opaque memory scoring** | Black-box relevance | Explainable attention scores shown in dashboard |
| **Cold-start problem** | Requires many interactions | Residual pathways preserve signal even with sparse data |
| **No sleep/consolidation** | Memories degrade silently | Nightly consolidation job improves retrieval quality over time |
| **One SDK** | Python only | Python + Node.js SDKs + REST |
| **Poor observability** | No usage dashboard | Real-time dashboard with memory health, drift, attention maps |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT APPLICATIONS                │
│          (LangChain, LlamaIndex, Raw API)            │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / SDK
┌──────────────────────▼──────────────────────────────┐
│                  API GATEWAY (FastAPI)               │
│   Auth → Rate Limit → Plan Check → Route            │
└──┬────────────────┬──────────────┬──────────────────┘
   │                │              │
┌──▼───┐     ┌──────▼────┐  ┌─────▼──────┐
│Memory│     │  Sleep    │  │  Attention │
│Store │     │ Scheduler │  │   Engine   │
│Layer │     │  (Celery) │  │  (Scoring) │
└──┬───┘     └──────┬────┘  └─────┬──────┘
   │                │              │
┌──▼────────────────▼──────────────▼──────────────────┐
│              PostgreSQL + pgvector                   │
│         (Memories, Embeddings, Tasks, Users)         │
└──────────────────────┬──────────────────────────────┘
                       │
           ┌───────────▼───────────┐
           │   Redis (Cache +      │
           │   Celery Broker)      │
           └───────────────────────┘
```

---

## 3. Core NeuroSleepNet Concepts (Enhanced)

### 3.1 Sleep-Inspired Replay (Enhanced)

**Original concept:** Periodic replay of past experiences.

**Enhancement:** Instead of full model replay, NeuroSleepNet uses **latent vector replay with temporal decay scoring**.

- Every memory gets a `consolidation_score` (0.0–1.0).
- A nightly Celery job ("Sleep Phase") runs at 2 AM IST.
- During sleep: memories with low consolidation score AND high access frequency get **reinforced** (score boosted, embedding refreshed).
- Memories with low score AND zero access get **pruned** (soft-deleted, archived to cold storage).
- This mimics slow-wave sleep (consolidation) and REM sleep (emotional/priority processing).

```python
# Pseudocode for sleep phase
for memory in memories.filter(last_accessed__lt=7_days_ago):
    if memory.access_count > threshold:
        memory.consolidation_score = min(1.0, memory.consolidation_score + 0.1)
        memory.embedding = re_embed(memory.content)  # refresh embedding
    elif memory.consolidation_score < 0.2:
        memory.status = "archived"
    memory.save()
```

### 3.2 Residual Memory Pathways (Enhanced)

**Original concept:** Residual connections for gradient flow.

**Enhancement:** Implemented as **memory inheritance chains**. When a new task is created, it inherits a compressed residual summary of semantically related past tasks. This prevents starting from zero.

- Each task stores a `residual_context` blob (compressed vector + top-5 concept tags).
- New memory writes check: "Is there a related task?" → inject residual context as a soft prior.
- This means even if you're in Task B, memories from semantically adjacent Task A don't vanish — they inform retrieval through a weighted residual path.

### 3.3 Task-Aware Attention Mechanism (Enhanced)

**Original concept:** Attention to prioritize task-relevant info.

**Enhancement:** A lightweight **attention scorer** that runs on every retrieval:

1. Query embedding is compared against all candidate memories.
2. Each memory gets an `attention_score` = cosine_similarity × recency_weight × consolidation_score.
3. Top-K memories are returned ranked by attention_score.
4. Scores are **exposed in the API response** (not hidden) — so developers can see why a memory was retrieved.

```json
{
  "memories": [
    {
      "id": "mem_xyz",
      "content": "User prefers dark mode",
      "attention_score": 0.91,
      "consolidation_score": 0.78,
      "why_retrieved": "High semantic similarity + recently accessed"
    }
  ]
}
```

---

## 4. Pricing Plans

### Free Tier — "Dreamer"

> **Philosophy:** Generous enough to build and ship a real product.

| Feature | Limit |
|---|---|
| Memory operations (read + write) | **10,000 / month** |
| Memory storage | **500 MB** |
| Sleep consolidation runs | **Weekly** (every Sunday 2 AM IST) |
| Tasks / namespaces | **10** |
| Residual context chains | **Basic** (depth-1 only) |
| Attention scoring | ✅ Included |
| API keys | **2** |
| SDK access (Python + Node) | ✅ |
| REST API | ✅ |
| Dashboard | ✅ Full access |
| Memory retention | **90 days** (then archived) |
| Rate limit | 60 req/min |
| Support | Community Discord |
| Sleep phase control | ❌ (automatic only) |
| Custom embedding models | ❌ |
| SSO / Team seats | ❌ |
| Export | JSON export only |

### Paid Tier — "Architect" — ₹999/month (or ₹9,999/year — save 2 months)

> **Philosophy:** Everything a production team needs.

| Feature | Limit |
|---|---|
| Memory operations | **Unlimited** |
| Memory storage | **50 GB** |
| Sleep consolidation runs | **Nightly** (custom time configurable) |
| Tasks / namespaces | **Unlimited** |
| Residual context chains | **Deep** (depth-5, cross-task) |
| Attention scoring | ✅ + Explainability traces |
| API keys | **Unlimited** |
| SDK access | ✅ Python + Node + Webhooks |
| REST API | ✅ + GraphQL (beta) |
| Dashboard | ✅ + Memory heat maps + Drift alerts |
| Memory retention | **Forever** (unless deleted) |
| Rate limit | 1,000 req/min |
| Support | Priority email + WhatsApp |
| Sleep phase control | ✅ Custom schedule + manual trigger |
| Custom embedding models | ✅ (bring your own OpenAI/Cohere key) |
| SSO / Team seats | ✅ Up to 10 seats |
| Export | JSON + CSV + Parquet |
| SLA | 99.9% uptime |
| Audit log | ✅ 90-day log |
| Webhook on sleep events | ✅ |

**Payment:** Razorpay — UPI, Net Banking, Credit/Debit Card, EMI (Bajaj/HDFC), Wallets (Paytm).

---

## 5. Folder Structure

> **AI Agent Instruction:** After cleanup (Step 0), create this exact structure.

```
neurosleepnet/
│
├── PLAN.md                        ← This file
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile                       ← Dev shortcuts
│
├── backend/                       ← FastAPI application (uv managed)
│   ├── pyproject.toml             ← uv project file (NOT requirements.txt)
│   ├── uv.lock
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   └── app/
│       ├── main.py                ← FastAPI app entry point
│       ├── config.py              ← Settings (pydantic-settings)
│       ├── deps.py                ← Shared dependencies (DB, auth)
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── v1/
│       │   │   ├── router.py      ← Mounts all v1 routes
│       │   │   ├── auth.py        ← Login, register, JWT
│       │   │   ├── memories.py    ← CRUD for memories
│       │   │   ├── tasks.py       ← Task namespace management
│       │   │   ├── search.py      ← Semantic search endpoint
│       │   │   ├── sleep.py       ← Manual sleep trigger (Paid)
│       │   │   ├── billing.py     ← Razorpay webhook + plan management
│       │   │   └── dashboard.py   ← Stats, usage, health metrics
│       │
│       ├── core/
│       │   ├── sleep_engine.py    ← Sleep-phase replay logic
│       │   ├── attention.py       ← Attention scoring + retrieval
│       │   ├── residual.py        ← Residual memory pathway builder
│       │   ├── embeddings.py      ← Embedding abstraction layer
│       │   └── consolidation.py   ← Consolidation score manager
│       │
│       ├── models/
│       │   ├── user.py
│       │   ├── memory.py
│       │   ├── task.py
│       │   ├── api_key.py
│       │   └── billing.py
│       │
│       ├── schemas/
│       │   ├── memory.py          ← Pydantic request/response models
│       │   ├── task.py
│       │   ├── auth.py
│       │   └── dashboard.py
│       │
│       ├── services/
│       │   ├── memory_service.py
│       │   ├── embedding_service.py
│       │   ├── billing_service.py
│       │   └── usage_service.py   ← Tracks op counts, enforces limits
│       │
│       ├── workers/
│       │   ├── celery_app.py      ← Celery setup
│       │   ├── sleep_tasks.py     ← Nightly consolidation job
│       │   └── cleanup_tasks.py   ← Prune archived memories
│       │
│       ├── middleware/
│       │   ├── rate_limit.py      ← Redis-backed rate limiter
│       │   ├── plan_check.py      ← Enforce free vs paid limits
│       │   └── audit_log.py       ← Paid-only audit trail
│       │
│       └── utils/
│           ├── crypto.py          ← API key hashing
│           ├── pagination.py
│           └── errors.py          ← Standardized error responses
│
├── sdk/
│   ├── python/                    ← PyPI package: neurosleepnet
│   │   ├── pyproject.toml
│   │   ├── neurosleepnet/
│   │   │   ├── __init__.py
│   │   │   ├── client.py          ← Main client class
│   │   │   ├── memory.py          ← Memory operations
│   │   │   ├── task.py
│   │   │   └── exceptions.py
│   │   └── tests/
│   │
│   └── node/                      ← npm package: neurosleepnet
│       ├── package.json
│       ├── src/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   └── types.ts
│       └── tests/
│
├── frontend/                      ← Pre-built (DO NOT MODIFY STRUCTURE)
│   └── ...                        ← Your existing frontend lives here
│
├── infra/
│   ├── nginx/
│   │   └── nginx.conf
│   └── scripts/
│       ├── init_db.sh
│       ├── backup.sh
│       └── seed_demo.py           ← Seeds demo memories for new users
│
└── docs/
    ├── quickstart.md
    ├── api-reference.md
    └── sdk-guide.md
```

---

## 6. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Runtime | Python 3.12 | Stable, ecosystem |
| Package manager | **uv** | 10-100x faster than pip |
| Web framework | FastAPI | Async, OpenAPI auto-docs |
| ORM | SQLAlchemy 2.0 (async) | Type-safe, alembic migrations |
| Database | PostgreSQL 16 + **pgvector** | Vector similarity built-in |
| Cache + broker | Redis 7 | Rate limiting + Celery |
| Task queue | Celery + Redis | Sleep phase cron jobs |
| Embeddings | OpenAI `text-embedding-3-small` (default) | Best price/performance; swappable |
| Auth | JWT (python-jose) + bcrypt | Stateless, secure |
| Payments | **Razorpay** | India-first, UPI/EMI support |
| Containerization | Docker + Docker Compose | Dev/prod parity |
| Reverse proxy | Nginx | TLS termination, rate limiting |
| Monitoring | Prometheus + Grafana (optional) | Ops visibility |
| Linting | ruff + mypy | Fast, strict |
| Testing | pytest + httpx | Async test support |

---

## 7. Database Schema

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',          -- 'free' | 'paid'
    razorpay_subscription_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);

-- API Keys (hashed, never stored plaintext)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,                      -- SHA-256 of actual key
    key_prefix TEXT NOT NULL,                    -- First 8 chars for display
    name TEXT,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Tasks (namespaces)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    residual_context JSONB,                      -- Compressed cross-task context
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Memories (core table)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),                      -- pgvector column
    metadata JSONB DEFAULT '{}',
    consolidation_score FLOAT DEFAULT 0.5,       -- 0.0 → pruned, 1.0 → permanent
    access_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',               -- 'active' | 'archived' | 'pruned'
    created_at TIMESTAMPTZ DEFAULT now(),
    last_accessed_at TIMESTAMPTZ DEFAULT now(),
    last_consolidated_at TIMESTAMPTZ
);

-- Vector index for similarity search
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Usage tracking (per user per month)
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    month TEXT NOT NULL,                         -- '2025-01'
    memory_reads INTEGER DEFAULT 0,
    memory_writes INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, month)
);

-- Audit log (paid only)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,                        -- 'memory.write', 'sleep.trigger', etc.
    metadata JSONB,
    ip TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 8. API Design

### Base URL
```
https://api.neurosleepnet.com/v1
```

### Authentication
```http
Authorization: Bearer nsn_live_xxxxxxxxxxxx
```

### Core Endpoints

```
POST   /memories              → Add a memory
GET    /memories              → List memories (paginated)
GET    /memories/{id}         → Get one memory
DELETE /memories/{id}         → Delete memory
POST   /memories/search       → Semantic search (returns attention scores)
POST   /memories/bulk         → Bulk write (up to 100)

GET    /tasks                 → List task namespaces
POST   /tasks                 → Create task
DELETE /tasks/{id}            → Delete task + associated memories

POST   /sleep/trigger         → Manual sleep run (Paid only)
GET    /sleep/history         → Past sleep run logs

GET    /dashboard/stats       → Usage, health score, memory counts
GET    /dashboard/attention   → Top memories by attention score
GET    /dashboard/drift       → Memory drift over time (staleness)

POST   /auth/register
POST   /auth/login
POST   /auth/refresh
GET    /auth/me

GET    /billing/plans
POST   /billing/subscribe     → Create Razorpay subscription
POST   /billing/webhook       → Razorpay event receiver
GET    /billing/usage         → Current month usage
```

### Example: Add Memory

```json
POST /v1/memories
{
  "content": "User prefers concise answers with code examples",
  "task_id": "task_abc123",
  "metadata": {
    "source": "chat",
    "agent_id": "assistant-v2"
  }
}

Response 201:
{
  "id": "mem_xyz789",
  "consolidation_score": 0.5,
  "status": "active",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Example: Semantic Search

```json
POST /v1/memories/search
{
  "query": "What does the user prefer about responses?",
  "task_id": "task_abc123",
  "top_k": 5,
  "min_attention_score": 0.3
}

Response 200:
{
  "memories": [
    {
      "id": "mem_xyz789",
      "content": "User prefers concise answers with code examples",
      "attention_score": 0.91,
      "consolidation_score": 0.78,
      "why_retrieved": "High semantic similarity (0.89) + recently accessed + high consolidation"
    }
  ],
  "sleep_last_run": "2025-01-15T02:00:00Z",
  "residual_context_applied": true
}
```

### SDK Usage (Python)

```python
from neurosleepnet import NeuroSleepNet

nsn = NeuroSleepNet(api_key="nsn_live_xxxx")

# Add memory
nsn.memories.add(
    content="User is a backend developer who prefers Python",
    task="user-profiling"
)

# Search with attention scores
results = nsn.memories.search(
    query="What language does the user prefer?",
    task="user-profiling",
    top_k=3
)

for mem in results:
    print(f"{mem.content} (attention: {mem.attention_score})")
```

### SDK Usage (Node.js)

```typescript
import { NeuroSleepNet } from 'neurosleepnet';

const nsn = new NeuroSleepNet({ apiKey: 'nsn_live_xxxx' });

await nsn.memories.add({
  content: 'User prefers TypeScript over JavaScript',
  task: 'user-profiling'
});

const results = await nsn.memories.search({
  query: 'programming language preference',
  task: 'user-profiling'
});
```

---

## 9. Dashboard Design

> Reference: mem0.ai dashboard. Improve on all weak points.

### Dashboard Sections (Post-Login)

#### 9.1 Overview Panel (Top Row — 4 cards)
- **Total Memories** — count + trend arrow vs last month
- **Operations This Month** — reads + writes with progress bar to limit
- **Memory Health Score** — aggregate consolidation score (0–100)
- **Last Sleep Run** — "3 hours ago" + status badge (Success / Partial / Pending)

#### 9.2 Memory Activity Chart
- Time-series chart: Reads vs Writes per day (last 30 days)
- Highlight sleep consolidation events as vertical markers on the chart

#### 9.3 Attention Heatmap
- Top 20 memories ranked by attention score, shown as a visual heatmap
- Click any memory to expand: content, score breakdown, access history, task

#### 9.4 Task Namespace Panel
- List of all tasks with: memory count, avg consolidation score, last accessed
- Click task → filtered memory view
- Quick "Create Task" button

#### 9.5 Memory Health Breakdown
- Pie chart: Active / Archived / At-risk (consolidation < 0.3)
- "At-risk" memories with a "Rescue" button → boosts consolidation score manually

#### 9.6 Sleep Phase Log
- Table: Date | Duration | Memories Consolidated | Memories Archived | Memories Pruned
- Manual trigger button (Paid plan badge if free)

#### 9.7 Quick Start / Integration
- Copy-paste SDK install command
- API key display (masked, with copy + rotate buttons)
- Links to docs, quickstart guide, Discord

#### 9.8 Billing Widget
- Free plan: Usage bar (ops used / 10,000), upgrade CTA
- Paid plan: Next billing date, Razorpay manage link, invoice download

---

## 10. Payment Integration (Razorpay)

### Setup

```python
# backend/app/services/billing_service.py
import razorpay

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_subscription(user_id: str, plan_id: str):
    subscription = client.subscription.create({
        "plan_id": RAZORPAY_PLAN_ID,          # ₹999/month plan created in Razorpay dashboard
        "total_count": 12,                     # 12 billing cycles
        "quantity": 1,
        "notify_info": {
            "notify_phone": "",                # Optional WhatsApp
            "notify_email": user_email
        }
    })
    return subscription["id"]
```

### Razorpay Plan IDs to Create

In Razorpay Dashboard → Products → Subscriptions → Plans:

| Plan | ID | Amount | Interval |
|---|---|---|---|
| Monthly | `plan_nsn_monthly` | ₹999 | Monthly |
| Annual | `plan_nsn_annual` | ₹9,999 | Yearly |

### Webhook Events to Handle

```python
@router.post("/billing/webhook")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    # Verify signature first (CRITICAL safety check)
    razorpay.utility.verify_webhook_signature(payload, signature, WEBHOOK_SECRET)
    
    event = await request.json()
    match event["event"]:
        case "subscription.activated":
            await upgrade_user_to_paid(event["payload"])
        case "subscription.charged":
            await extend_billing_cycle(event["payload"])
        case "subscription.cancelled" | "subscription.expired":
            await downgrade_user_to_free(event["payload"])
        case "payment.failed":
            await send_payment_failure_email(event["payload"])
```

### Frontend Payment Flow

```
User clicks "Upgrade" 
  → POST /v1/billing/subscribe (returns Razorpay subscription_id + key)
  → Frontend opens Razorpay Checkout modal
  → User pays via UPI / Card / NetBanking / EMI
  → Razorpay fires webhook to /v1/billing/webhook
  → User's plan updated to "paid" in DB
  → Dashboard refreshes with paid features unlocked
```

---

## 11. Fallback & Safety Mechanisms

### 11.1 Embedding Failures

```python
# embeddings.py
async def get_embedding(text: str) -> list[float]:
    try:
        return await openai_embed(text)
    except Exception as e:
        logger.warning(f"Primary embedding failed: {e}")
        try:
            return await fallback_embed_local(text)  # sentence-transformers local model
        except Exception:
            raise EmbeddingUnavailableError("Both embedding providers failed")
```

### 11.2 Database Connection Fallback

```python
# deps.py
async def get_db():
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except OperationalError:
        # Log + return 503 with retry-after header
        raise DatabaseUnavailableError()
```

### 11.3 Rate Limiting (Redis-backed)

```python
# middleware/rate_limit.py
LIMITS = {
    "free": "60/minute",
    "paid": "1000/minute"
}

async def rate_limit_middleware(request: Request, call_next):
    user = get_user_from_request(request)
    key = f"rate:{user.id}:{int(time.time() // 60)}"
    count = await redis.incr(key)
    await redis.expire(key, 60)
    
    limit = 60 if user.plan == "free" else 1000
    if count > limit:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after": 60}
        )
    return await call_next(request)
```

### 11.4 Sleep Phase Safety Checks

```python
# workers/sleep_tasks.py
@celery_app.task
def run_sleep_phase(user_id: str = None):
    """Safety checks before any sleep consolidation."""
    
    # Check 1: Never prune memories that are less than 72 hours old
    # Check 2: Never archive more than 20% of a user's memories in one run
    # Check 3: Always keep at least 50 memories per task (if they exist)
    # Check 4: Require consolidation_score < 0.15 AND access_count == 0 for pruning
    # Check 5: Log every action — full audit trail regardless of plan
    
    with db_session() as db:
        memories = db.query(Memory).filter(
            Memory.status == "active",
            Memory.last_accessed_at < datetime.now() - timedelta(days=7),
            Memory.consolidation_score < 0.15,
            Memory.access_count == 0,
            Memory.created_at < datetime.now() - timedelta(hours=72)  # Safety: 72hr minimum
        ).limit(max_prune_count)    # max_prune_count = 20% of user's total
        
        for memory in memories:
            memory.status = "archived"
            log_sleep_action(memory.id, "archived")
```

### 11.5 Plan Limit Enforcement

```python
# middleware/plan_check.py
PLAN_LIMITS = {
    "free": {
        "monthly_ops": 10_000,
        "storage_bytes": 500 * 1024 * 1024,   # 500 MB
        "max_tasks": 10,
        "max_api_keys": 2
    },
    "paid": {
        "monthly_ops": float("inf"),
        "storage_bytes": 50 * 1024 * 1024 * 1024,  # 50 GB
        "max_tasks": float("inf"),
        "max_api_keys": float("inf")
    }
}

async def check_plan_limits(user, operation: str):
    limits = PLAN_LIMITS[user.plan]
    usage = await get_current_usage(user.id)
    
    if usage.monthly_ops >= limits["monthly_ops"]:
        raise PlanLimitError(
            f"Monthly limit of {limits['monthly_ops']:,} operations reached. "
            "Upgrade to Architect plan for unlimited operations.",
            upgrade_url="https://neurosleepnet.com/upgrade"
        )
```

### 11.6 API Key Security

```python
# utils/crypto.py
import secrets, hashlib

def generate_api_key() -> tuple[str, str]:
    """Returns (plaintext_key, hashed_key). Only plaintext shown once."""
    raw = "nsn_live_" + secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:16]  # Store prefix for display (nsn_live_xxxxxxxx)
    return raw, hashed, prefix

def verify_api_key(provided: str, stored_hash: str) -> bool:
    provided_hash = hashlib.sha256(provided.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, stored_hash)
```

---

## 12. Docker & Deployment

### docker-compose.yml (Development)

```yaml
version: "3.9"

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://nsn:nsn@db:5432/neurosleepnet
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - RAZORPAY_KEY_ID=${RAZORPAY_KEY_ID}
      - RAZORPAY_KEY_SECRET=${RAZORPAY_KEY_SECRET}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend:/app
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://nsn:nsn@db:5432/neurosleepnet
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    command: uv run celery -A app.workers.celery_app worker --loglevel=info -B

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: neurosleepnet
      POSTGRES_USER: nsn
      POSTGRES_PASSWORD: nsn
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nsn -d neurosleepnet"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api

volumes:
  pgdata:
```

### backend/Dockerfile

```dockerfile
FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### backend/pyproject.toml

```toml
[project]
name = "neurosleepnet-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pgvector>=0.3.0",
    "redis[hiredis]>=5.2.0",
    "celery[redis]>=5.4.0",
    "openai>=1.57.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "razorpay>=1.4.0",
    "pydantic-settings>=2.7.0",
    "httpx>=0.27.0",
    "sentence-transformers>=3.3.0",   # Fallback embeddings
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
    "mypy>=1.14.0",
]
```

### Makefile

```makefile
.PHONY: up down migrate seed test lint

up:
	docker compose up --build -d

down:
	docker compose down -v

migrate:
	docker compose exec api uv run alembic upgrade head

seed:
	docker compose exec api uv run python infra/scripts/seed_demo.py

test:
	cd backend && uv run pytest tests/ -v

lint:
	cd backend && uv run ruff check . && uv run mypy .

logs:
	docker compose logs -f api worker

shell:
	docker compose exec api uv run python
```

---

## 13. Implementation Checkpoints

> **AI Agent Instruction:** After completing each checkpoint, add `[x]` before committing.
> Never skip a checkpoint. If a step fails, fix it before proceeding.

---

### Phase 0 — Cleanup & Scaffold
- [ ] **CP-00** Delete existing folder structure as described in Step 0 cleanup block
- [ ] **CP-01** Install `uv` on the host machine
- [ ] **CP-02** Run `uv init neurosleepnet-backend` — confirm `pyproject.toml` exists
- [ ] **CP-03** Create full folder structure as defined in Section 5
- [ ] **CP-04** Copy `.env.example` with all required keys documented

---

### Phase 1 — Database & Core Models
- [ ] **CP-05** `docker compose up db redis -d` — verify both healthy
- [ ] **CP-06** Alembic initialized — `alembic init alembic/` — `env.py` connected to async DB
- [ ] **CP-07** All SQLAlchemy models created (users, api_keys, tasks, memories, usage_logs, audit_logs)
- [ ] **CP-08** `alembic revision --autogenerate -m "initial"` — migration file generated
- [ ] **CP-09** `alembic upgrade head` — all tables created in DB
- [ ] **CP-10** pgvector extension enabled — `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] **CP-11** Vector index created on `memories.embedding`

---

### Phase 2 — Auth & API Keys
- [ ] **CP-12** `POST /v1/auth/register` working — returns JWT
- [ ] **CP-13** `POST /v1/auth/login` working — bcrypt password verify
- [ ] **CP-14** `GET /v1/auth/me` working — JWT decode + user lookup
- [ ] **CP-15** API key generation (`nsn_live_...`) — plaintext shown once, hash stored
- [ ] **CP-16** API key middleware — all `/v1/memories*` routes protected
- [ ] **CP-17** Rate limit middleware wired up — Redis counter verified

---

### Phase 3 — Memory CRUD
- [ ] **CP-18** `POST /v1/memories` — writes memory + generates embedding
- [ ] **CP-19** Embedding stored as `VECTOR(1536)` in pgvector — verify with `SELECT embedding IS NOT NULL`
- [ ] **CP-20** `GET /v1/memories` — paginated list, filtered by task
- [ ] **CP-21** `DELETE /v1/memories/{id}` — soft-delete sets status = 'pruned'
- [ ] **CP-22** Usage tracking — `usage_logs` incremented on every write/read
- [ ] **CP-23** Plan limit check — free user blocked at 10,001st operation

---

### Phase 4 — Attention-Scored Search
- [ ] **CP-24** `POST /v1/memories/search` — cosine similarity via pgvector `<=>` operator
- [ ] **CP-25** Attention score computed: cosine_sim × recency_weight × consolidation_score
- [ ] **CP-26** `why_retrieved` explanation string generated per result
- [ ] **CP-27** Residual context applied (task's `residual_context` injected into search)
- [ ] **CP-28** `min_attention_score` filter working

---

### Phase 5 — Sleep Engine
- [ ] **CP-29** Celery worker starts — `uv run celery -A app.workers.celery_app worker`
- [ ] **CP-30** `sleep_tasks.py` registered as periodic task (Celery Beat — 2 AM IST for free, configurable for paid)
- [ ] **CP-31** All 5 safety checks implemented (age guard, 20% cap, 50-memory minimum, score threshold, 72hr minimum)
- [ ] **CP-32** Sleep run logged to `audit_logs` with full action breakdown
- [ ] **CP-33** `POST /v1/sleep/trigger` endpoint — 403 for free users, works for paid
- [ ] **CP-34** `GET /v1/sleep/history` returns last 10 runs with stats

---

### Phase 6 — Dashboard API
- [ ] **CP-35** `GET /v1/dashboard/stats` returns: total memories, monthly ops, health score, last sleep run
- [ ] **CP-36** `GET /v1/dashboard/attention` returns top 20 memories by score
- [ ] **CP-37** `GET /v1/dashboard/drift` returns stale memory count + at-risk count

---

### Phase 7 — Billing (Razorpay)
- [ ] **CP-38** Razorpay SDK installed and credentials verified (test mode first)
- [ ] **CP-39** Monthly and annual plans created in Razorpay dashboard — plan IDs saved to `.env`
- [ ] **CP-40** `POST /v1/billing/subscribe` — creates Razorpay subscription, returns checkout params
- [ ] **CP-41** Webhook endpoint verified with Razorpay signature check
- [ ] **CP-42** `subscription.activated` → user plan updated to 'paid' in DB
- [ ] **CP-43** `subscription.cancelled` → user plan downgraded to 'free', limits re-enforced
- [ ] **CP-44** `GET /v1/billing/usage` returns current month usage + limits

---

### Phase 8 — SDKs
- [ ] **CP-45** Python SDK (`sdk/python/`) — `pip install neurosleepnet` works in test env
- [ ] **CP-46** Python SDK: `memories.add()`, `memories.search()`, `memories.list()` all tested
- [ ] **CP-47** Node SDK (`sdk/node/`) — `npm install neurosleepnet` works in test env
- [ ] **CP-48** Node SDK: same operations work with TypeScript types

---

### Phase 9 — Frontend Integration
- [ ] **CP-49** Frontend `.env` updated with `VITE_API_URL=http://localhost:8000/v1`
- [ ] **CP-50** Auth flow (register/login) connects to real backend
- [ ] **CP-51** Dashboard stats cards populated from `GET /v1/dashboard/stats`
- [ ] **CP-52** Memory list view renders from `GET /v1/memories`
- [ ] **CP-53** Search UI sends to `POST /v1/memories/search` and shows attention scores
- [ ] **CP-54** Billing upgrade button triggers Razorpay checkout modal

---

### Phase 10 — Hardening & Deployment
- [ ] **CP-55** `docker compose up --build` brings all services up cleanly
- [ ] **CP-56** `make migrate` runs successfully inside Docker
- [ ] **CP-57** `make seed` populates demo user with 50 sample memories
- [ ] **CP-58** `make test` — all tests pass (>80% coverage target)
- [ ] **CP-59** Nginx config routes `/api/v1/*` to FastAPI, `/` to frontend
- [ ] **CP-60** Fallback embedding (local sentence-transformers) tested — triggers when OpenAI fails
- [ ] **CP-61** Razorpay webhook tested end-to-end with Razorpay test events
- [ ] **CP-62** `docker-compose.prod.yml` created with resource limits, no volume mounts for source
- [ ] **CP-63** `.env.example` complete — no secrets committed to git
- [ ] **CP-64** README.md written with quickstart in under 5 commands

---

## Appendix A — Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=postgresql+asyncpg://nsn:nsn@db:5432/neurosleepnet

# Redis
REDIS_URL=redis://redis:6379/0

# Auth
JWT_SECRET=change-this-to-a-random-64-char-string
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# OpenAI (embeddings)
OPENAI_API_KEY=sk-...

# Razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
RAZORPAY_PLAN_ID_MONTHLY=plan_...
RAZORPAY_PLAN_ID_ANNUAL=plan_...

# App
APP_ENV=development        # development | production
FRONTEND_URL=http://localhost:3000
SLEEP_PHASE_HOUR=2         # 2 AM IST
SLEEP_PHASE_MINUTE=0
```

---

## Appendix B — Quick Start (For README)

```bash
# 1. Clone and configure
git clone https://github.com/your-org/neurosleepnet
cp .env.example .env   # Fill in your keys

# 2. Start everything
make up

# 3. Run migrations
make migrate

# 4. Seed demo data
make seed

# 5. Open dashboard
open http://localhost:3000

# API docs at: http://localhost:8000/docs
```

---

*NeuroSleepNet — Where AI memory never forgets what matters.*