# NeuroSleepNet — Audit Fix Implementation Guide

> Work through this file top to bottom. Every fix is self-contained.
> Do not skip ahead. Some fixes have dependencies on earlier ones.
> Commit after every section marked **[COMMIT POINT]**.

---

## Phase 1 — Critical Security & Correctness (🔴 Fixes 1–6)

These must be done before anything else. They affect correctness and security
on every request.

---

### Fix 1 — Re-enable RateLimitMiddleware

**File:** `backend/app/main.py`

**Why:** The plan mandates rate limiting as non-optional security. It is
currently commented out, meaning any client can hammer the API without
restriction.

**Step 1.1 — Find the commented line**
```python
# app.add_middleware(RateLimitMiddleware)   ← around line 36
```

**Step 1.2 — Before uncommenting, verify RateLimitMiddleware is wired
correctly. Open `backend/app/middleware/rate_limit.py` and confirm:**
- It reads from `app.state.redis` (not creating its own connection)
- It uses a token bucket keyed on `(project_id, client_ip)`
- It returns HTTP 429 with a `Retry-After` header on breach
- It does NOT block health check endpoints (`/health`, `/api/v1/health/deep`)

**Step 1.3 — If the middleware has a bug, fix it first. Common issues:**
```python
# WRONG — creates a new Redis connection per request
redis = Redis.from_url(settings.REDIS_URL)

# RIGHT — uses the shared pool from app state
redis = request.app.state.redis
```

**Step 1.4 — Uncomment the middleware registration:**
```python
app.add_middleware(RateLimitMiddleware)
```

**Step 1.5 — Verify it works:**
```bash
# Hit the same endpoint 20 times fast — should get 429 on breach
for i in $(seq 1 25); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer nsn_sk_test" \
    http://localhost:8000/api/v1/stats
done
```

---

### Fix 2 — O(N) API Key Scan → Prefix-Filtered Lookup

**File:** `backend/app/api/v1/auth.py` (around lines 59–63)

**Why:** The current implementation loads ALL active API keys and bcrypt-
compares each one on every authenticated request. This is O(N) in CPU and
latency as users grow.

**Step 2.1 — Confirm the `key_prefix` column exists in the ApiKey model:**
```python
# backend/app/models/api_key.py — should have:
key_prefix: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
```
If the column is missing, add it and create a migration:
```bash
cd backend
alembic revision --autogenerate -m "add key_prefix to api_keys"
alembic upgrade head
```

**Step 2.2 — Update `keygen.py` to store the prefix on key creation:**
```python
# sdk/python/neurosleepnet/keygen.py
import secrets, hashlib

def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix)"""
    raw = "nsn_sk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:12]   # "nsn_sk_" + first 5 chars — enough to narrow to 1 row
    return raw, key_hash, key_prefix
```

**Step 2.3 — Replace the O(N) verification loop in `auth.py`:**
```python
# BEFORE (O(N) — delete this)
stmt = select(ApiKey).where(ApiKey.is_active == True)
res = await db.execute(stmt)
keys = res.scalars().all()
for k in keys:
    if verify_api_key(token, k.key_hash):
        return k

# AFTER (O(1) in practice — replace with this)
key_prefix = token[:12]
stmt = (
    select(ApiKey)
    .where(ApiKey.is_active == True)
    .where(ApiKey.key_prefix == key_prefix)
)
res = await db.execute(stmt)
candidate = res.scalar_one_or_none()
if candidate and verify_api_key(token, candidate.key_hash):
    # Update last_used_at without blocking the request
    candidate.last_used_at = datetime.utcnow()
    await db.commit()
    return candidate
return None
```

**Step 2.4 — Run auth tests:**
```bash
cd backend
pytest tests/test_auth.py -v
```

---

### Fix 3 — `wrap()` Hardcoded `model_family="generic"`

**File:** `sdk/python/neurosleepnet/__init__.py` (around line 657)

**Why:** `wrap()` already detects the model name but never uses it for
context placement. This silently defeats the plan's key SLM differentiation.

**Step 3.1 — Add the family mapping dict near the top of `__init__.py`
(outside any function, at module level):**
```python
_MODEL_FAMILY_MAP: dict[str, str] = {
    "phi":     "phi3",
    "mistral": "mistral",
    "gemma":   "gemma",
    "llama":   "llama3",
}

def _detect_model_family(model_name: str) -> str:
    """Map a model name string to a context.py model_family key."""
    if not model_name:
        return "generic"
    name_lower = model_name.lower()
    for key, family in _MODEL_FAMILY_MAP.items():
        if key in name_lower:
            return family
    return "generic"
```

**Step 3.2 — Also add `model_family` as a configurable default in `nsn.init()`:**
```python
# In nsn.init() — add to the config object
_config["model_family"] = model_family  # new param, default "generic"

# Full updated signature:
def init(
    project: str,
    mode: str = "local",
    host: str = "http://localhost:8000",
    api_key: str | None = None,
    memory_window: int = 4096,
    sleep_interval: int = 300,
    sleep_on_exit: bool = True,
    embed_model: str = "local",
    recall_threshold: float = 0.6,
    implicit_feedback: bool = True,
    decay: bool = True,
    model_family: str = "generic",   # ← ADD THIS
    debug: bool = False,
): ...
```

**Step 3.3 — Fix the hardcoded call in `wrap()`:**
```python
# BEFORE
ctx_str = build_context(
    ...
    model_family="generic",
)

# AFTER
# Determine family: explicit arg on wrap() > detected from fn name > init() default
_wrap_family = (
    model_family                              # if passed explicitly to wrap()
    or _detect_model_family(fn.__name__)      # try to detect from function name
    or _config.get("model_family", "generic") # fall back to init() config
)

ctx_str = build_context(
    ...
    model_family=_wrap_family,
)
```

**Step 3.4 — Also fix `nsn.context()` to use the config default:**
```python
def context(
    query: str,
    user_id: str | None = None,
    max_tokens: int = 512,
    model_family: str | None = None,   # None = use init() config default
    format: str = "auto",
    include_pins: bool = True,
    min_score: float | None = None,
) -> str:
    _family = model_family or _config.get("model_family", "generic")
    return build_context(..., model_family=_family)
```

**Step 3.5 — Test:**
```python
import nsn
nsn.init(project="test", model_family="phi3")
ctx = nsn.context("debug my code", user_id="u1")
# Should contain phi3-formatted system prefix, not generic prepend
assert "<|system|>" in ctx or "<<SYS>>" in ctx  # adjust for your phi3 template
```

---

### Fix 4 — stats() Variable Naming + Add Hit Count + Token Savings

**File:** `sdk/python/neurosleepnet/local_store.py` (around line 459)

**Why:** `hits` variable queries `miss_log` (logically inverted name). No
`recall_hit_count` is returned. `token_savings` column exists but is never
updated and never returned.

**Step 4.1 — Fix the variable name and add missing fields in `get_stats()`:**
```python
def get_stats(self, project: str) -> dict:
    with self._conn() as conn:
        c = conn.cursor()

        total = c.execute(
            "SELECT COUNT(*) FROM memories WHERE project_id=? AND archived=0",
            (project,)
        ).fetchone()[0]

        by_type = {}
        for row in c.execute(
            "SELECT memory_type, COUNT(*) FROM memories "
            "WHERE project_id=? AND archived=0 GROUP BY memory_type",
            (project,)
        ).fetchall():
            by_type[row[0]] = row[1]

        pinned_count = c.execute(
            "SELECT COUNT(*) FROM memories WHERE project_id=? AND pinned=1 AND archived=0",
            (project,)
        ).fetchone()[0]

        archived_count = c.execute(
            "SELECT COUNT(*) FROM memories WHERE project_id=? AND archived=1",
            (project,)
        ).fetchone()[0]

        # FIX: was named "hits" but queries miss_log — rename correctly
        miss_count = c.execute(
            "SELECT COUNT(*) FROM miss_log WHERE project_id=?",
            (project,)
        ).fetchone()[0]

        # Hit count: sum of access_count across all active memories
        # (approximation — each access was a successful recall)
        recall_hit_count = c.execute(
            "SELECT COALESCE(SUM(access_count), 0) FROM memories "
            "WHERE project_id=? AND archived=0",
            (project,)
        ).fetchone()[0]

        total_recalls = recall_hit_count + miss_count
        recall_hit_rate = (
            round(recall_hit_count / total_recalls, 3)
            if total_recalls > 0 else 0.0
        )
        recall_miss_rate = (
            round(miss_count / total_recalls, 3)
            if total_recalls > 0 else 0.0
        )

        # token_savings from project_meta
        token_savings = c.execute(
            "SELECT COALESCE(token_savings, 0) FROM project_meta WHERE project_id=?",
            (project,)
        ).fetchone()
        token_savings = token_savings[0] if token_savings else 0

        sleep_row = c.execute(
            "SELECT COUNT(*), COALESCE(SUM(memories_consolidated),0), "
            "COALESCE(SUM(dupes_removed),0) "
            "FROM sleep_log WHERE project_id=?",
            (project,)
        ).fetchone()

        return {
            "total_memories":        total,
            "by_type":               by_type,
            "pinned":                pinned_count,
            "archived":              archived_count,
            "recall_hit_count":      recall_hit_count,
            "miss_count":            miss_count,
            "recall_hit_rate":       recall_hit_rate,
            "recall_miss_rate":      recall_miss_rate,
            "token_savings_estimate":token_savings,
            "sleep_cycles_run":      sleep_row[0],
            "memories_consolidated": sleep_row[1],
            "dupes_removed":         sleep_row[2],
        }
```

**Step 4.2 — Wire `token_savings` update in `retrieve()`:**
```python
# In local_store.py retrieve() — after selecting top-k memories to inject,
# add at the end of the method:

# Estimate tokens saved = tokens in ALL memories - tokens in injected subset
all_content_tokens = sum(
    len(m["content"]) // 4
    for m in all_candidates   # full candidate list before top-k slice
)
injected_tokens = sum(
    len(m["content"]) // 4
    for m in results          # the top-k returned
)
savings_delta = max(0, all_content_tokens - injected_tokens)

if savings_delta > 0:
    conn.execute(
        "UPDATE project_meta SET token_savings = COALESCE(token_savings,0) + ? "
        "WHERE project_id=?",
        (savings_delta, project)
    )
    conn.commit()
```

---

### Fix 5 — CORS `allow_origins=["*"]` → Env-Configurable

**File:** `backend/app/main.py` (around line 28)

**Why:** `allow_origins=["*"]` with `allow_credentials=True` is a browser
CORS error in practice AND a security misconfiguration. Browsers reject
wildcard + credentials.

**Step 5.1 — Add to `backend/app/config.py`:**
```python
ALLOWED_ORIGINS: list[str] = Field(
    default=["http://localhost:3000", "http://localhost:8080"],
    description="Comma-separated list of allowed CORS origins"
)

# Pydantic v2 validator to parse comma-separated env string:
@field_validator("ALLOWED_ORIGINS", mode="before")
@classmethod
def parse_origins(cls, v):
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(",")]
    return v
```

**Step 5.2 — Update the CORSMiddleware in `main.py`:**
```python
# BEFORE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)

# AFTER
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Project-ID"],
)
```

**Step 5.3 — Update `.env.example`:**
```bash
# Comma-separated list of allowed CORS origins
# Dev default: http://localhost:3000,http://localhost:8080
# Prod: set to your actual domain
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

### Fix 6 — `/health` Hardcoded `"ok"` → Real Checks

**File:** `backend/app/main.py` (around line 65)

**Why:** Docker and load-balancers use `/health` for liveness probes. A
hardcoded `"ok"` means a broken DB or Redis goes undetected.

**Step 6.1 — Replace the shallow `/health` handler:**
```python
@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    checks = {}
    overall = "ok"

    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {str(e)[:80]}"
        overall = "degraded"

    # Check Redis
    try:
        redis = request.app.state.redis
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:80]}"
        overall = "degraded"

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "version": settings.VERSION,
            **checks,
        }
    )
```

**Step 6.2 — Remove or alias `/api/v1/health/deep` if it now duplicates `/health`.**

---

**[COMMIT POINT]**
```
fix: resolve all 6 critical audit issues

- re-enable RateLimitMiddleware in main.py
- fix O(N) API key scan → prefix-filtered single-row lookup
- fix wrap() hardcoded model_family="generic" → detected + configurable
- fix stats() hits/miss naming, add recall_hit_count, wire token_savings
- fix CORS allow_origins wildcard → env-configurable ALLOWED_ORIGINS
- fix /health hardcoded "ok" → real DB + Redis liveness checks
```

---

## Phase 2 — Important Plan Compliance (🟡 Fixes 7–14)

These are plan features that are present but not fully wired. Complete them
in order.

---

### Fix 7 — Add `merge_projects` to `nsn/` Re-exports

**File:** `sdk/python/nsn/__init__.py`

**Why:** It is in `neurosleepnet.__all__` but not explicitly imported in
the alias package. IDE autocomplete and `from nsn import merge_projects`
both silently fail.

**Step 7.1 — Open `sdk/python/nsn/__init__.py`. Find the explicit import
list. Add `merge_projects`:**
```python
from neurosleepnet import (
    init,
    wrap,
    remember,
    recall,
    forget,
    forget_user,
    forget_project,
    pin,
    unpin,
    list_pins,
    feedback,
    feedback_batch,
    sleep,
    sleep_status,
    sleep_pause,
    sleep_resume,
    list_memories,
    search,
    stats,
    export,
    import_memories,
    dashboard,
    context,
    merge_projects,   # ← ADD THIS
)
```

**Step 7.2 — Verify:**
```python
python -c "from nsn import merge_projects; print('ok')"
```

---

### Fix 8 — Wire `token_savings` Update in `retrieve()`

Already covered in Fix 4 Step 4.2. If you did Fix 4 completely, this is done.
Double-check by running:
```python
import nsn
nsn.init(project="savings-test")
nsn.remember("User prefers TypeScript", user_id="u1", type="semantic")
nsn.remember("User hates semicolons", user_id="u1", type="semantic")
nsn.remember("User works at Stripe", user_id="u1", type="semantic")
nsn.recall("coding style", user_id="u1", top_k=1)  # injects 1, saves 2
s = nsn.stats()
assert s["token_savings_estimate"] > 0, "token_savings not being updated"
print("token_savings:", s["token_savings_estimate"])
```

---

### Fix 9 — Add Episodic → Semantic Promotion to Celery Sleep Engine

**File:** `backend/app/core/sleep_engine.py`

**Why:** The Docker backend's Celery worker runs the production sleep cycle
but skips the promotion phase. Memories never graduate from episodic to
semantic in self-host mode.

**Step 9.1 — Open `sleep_engine.py`. Find `run_sleep_phase()`. Add Step 3.5
after the boost phase, before the archive phase:**

```python
async def _promote_episodic_to_semantic(
    project_id: str,
    db: AsyncSession,
    qdrant: QdrantClient,
) -> int:
    """
    Promote episodic memories to semantic when consolidation_score >= 0.75.
    Returns count of promoted memories.
    """
    stmt = (
        select(Memory)
        .where(Memory.project_id == project_id)
        .where(Memory.memory_type == "episodic")
        .where(Memory.archived == False)
        .where(
            or_(
                Memory.consolidation_score >= 0.75,
                Memory.access_count >= 3,
            )
        )
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    promoted = 0
    for mem in candidates:
        mem.memory_type = "semantic"
        mem.updated_at = datetime.utcnow()
        promoted += 1

    if promoted > 0:
        await db.commit()

    return promoted
```

**Step 9.2 — Call it inside `run_sleep_phase()`:**
```python
async def run_sleep_phase(project_id: str, db: AsyncSession, qdrant: QdrantClient):
    stats = {}

    # Step 1 — Boost (existing)
    stats["boosted"] = await _boost_phase(project_id, db)

    # Step 2 — Dedup (existing)
    stats["dupes_removed"] = await _dedup_phase(project_id, db, qdrant)

    # Step 3 — Decay (existing)
    stats["decayed"] = await _decay_phase(project_id, db)

    # Step 3.5 — Promote episodic → semantic (NEW)
    stats["promotions"] = await _promote_episodic_to_semantic(project_id, db, qdrant)

    # Step 4 — Archive (existing)
    stats["archived"] = await _archive_phase(project_id, db)

    # Step 5 — Log to sleep_log (existing)
    await _log_sleep_cycle(project_id, db, stats)

    return stats
```

**Step 9.3 — Verify promotions appear in sleep status:**
```python
# After a sleep cycle, stats["promotions"] should be > 0
# if there are episodic memories meeting the threshold
nsn.init(project="promo-test", mode="self-host", host="http://localhost:8000",
         api_key="your-key")
for i in range(5):
    nsn.remember(f"User prefers tabs not spaces session {i}",
                 user_id="u1", type="episodic")
nsn.sleep()
import time; time.sleep(3)
status = nsn.sleep_status()
print("promotions:", status)  # check promotions > 0
```

---

### Fix 10 — Add `model_family` Default to `nsn.init()` Config

Already covered fully in Fix 3 Steps 3.1–3.4. Verify with:
```python
import nsn
nsn.init(project="test", model_family="mistral")
# All subsequent nsn.context() calls should default to mistral template
ctx = nsn.context("what do I prefer?", user_id="u1")
# Should use mistral injection position without passing model_family explicitly
```

---

### Fix 11 — Apply Threshold Gating in Self-Host `recall()` Path

**File:** `sdk/python/neurosleepnet/__init__.py` (around lines 325–336)

**Why:** The local path gates by `recall_threshold` and logs misses. The
self-host path skips both — memories below threshold pass through silently.

**Step 11.1 — Locate the self-host recall path. It should look something
like:**
```python
if _config.get("mode") == "self-host":
    raw = _remote_call("retrieve", query=query, user_id=user_id, top_k=top_k, ...)
    return [Memory(**m) for m in raw.get("memories", [])]
```

**Step 11.2 — Replace with threshold-gated version. Option A (preferred) —
pass `min_score` to the API so the server does the gating:**
```python
if _config.get("mode") == "self-host":
    threshold = min_score or _config.get("recall_threshold", 0.6)
    response = _remote_call(
        "POST", "/api/v1/recall",
        json={
            "query": query,
            "user_id": user_id,
            "top_k": top_k,
            "memory_types": memory_types,
            "min_score": threshold,   # ← server applies gating
        }
    )
    memories = [Memory(**m) for m in response.get("memories", [])]
    # Server already logged misses server-side via miss_log table
    return memories
```

**Step 11.3 — Confirm the `/api/v1/recall` router actually applies `min_score`
gating. Open `backend/app/api/v1/routers/recall.py` and check:**
```python
# Should have something like:
if memory.score < request.min_score:
    await log_miss(db, project_id, user_id, request.query, memory.score, request.min_score)
    continue   # skip this memory
```
If it doesn't — add it.

---

### Fix 12 — Fix Redis Connection Leak in Health Check

**File:** `backend/app/api/v1/health.py` (around line 32)

**Why:** A new Redis connection is opened on every health check call and
never closed. Under load this exhausts the connection pool.

**Step 12.1 — If Redis is already stored on `app.state`, use it:**
```python
# BEFORE — leaks a connection
redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
await redis.ping()

# AFTER — uses shared pool
from fastapi import Request

@router.get("/deep")
async def deep_health(request: Request, db: AsyncSession = Depends(get_db)):
    redis = request.app.state.redis   # shared pool, no leak
    await redis.ping()
    ...
```

**Step 12.2 — Confirm `app.state.redis` is set in the lifespan handler
in `main.py`:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    yield
    # Shutdown
    await app.state.redis.aclose()
```
If this pattern isn't present, add it.

---

### Fix 13 — Remove Hardcoded `NSN_ENCRYPTION_MASTER_KEY` Default

**File:** `docker-compose.yml` (around line 12)

**Why:** A hardcoded default encryption key means every copy-paste deployer
uses the same key. All their memory content is encrypted with the same secret.
This defeats the encryption entirely.

**Step 13.1 — Open `docker-compose.yml`. Find:**
```yaml
NSN_ENCRYPTION_MASTER_KEY: "changeme-in-production-32chars!!"
```

**Step 13.2 — Remove the default value entirely. Make it required:**
```yaml
# REQUIRED — generate with:
#   python -c "import secrets; print(secrets.token_hex(16))"
NSN_ENCRYPTION_MASTER_KEY: ${NSN_ENCRYPTION_MASTER_KEY:?NSN_ENCRYPTION_MASTER_KEY is required. See .env.example}
```
The `:?` syntax makes Docker Compose exit with an error message if the
variable is not set. This is intentional — deployers must set it explicitly.

**Step 13.3 — Update `.env.example`:**
```bash
# REQUIRED. Generate with:
#   python -c "import secrets; print(secrets.token_hex(16))"
# Never commit the actual value. Never reuse across projects.
NSN_ENCRYPTION_MASTER_KEY=
```

**Step 13.4 — Add a startup check in `backend/app/main.py` that refuses to
start if the key is the old default:**
```python
@app.on_event("startup")
async def validate_encryption_key():
    key = settings.NSN_ENCRYPTION_MASTER_KEY
    forbidden = {"changeme-in-production-32chars!!", "changeme", "secret", ""}
    if key in forbidden or len(key) < 32:
        raise RuntimeError(
            "NSN_ENCRYPTION_MASTER_KEY is insecure or not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(16))\""
        )
```

---

### Fix 14 — Rename `core/crypto.py` → `core/content_encryption.py`

**File:** `backend/app/core/crypto.py` → `backend/app/core/content_encryption.py`

**Why:** Two modules named `crypto` in different packages causes import
confusion. `core/crypto.py` handles AES-256 content encryption.
`utils/crypto.py` handles password hashing and key generation. The names
must be unambiguous.

**Step 14.1 — Rename the file:**
```bash
cd backend/app/core
git mv crypto.py content_encryption.py
```

**Step 14.2 — Update every import site. Find them all:**
```bash
grep -r "from.*core.crypto import\|from.*core import crypto" backend/ --include="*.py"
```

**Step 14.3 — Replace each occurrence:**
```python
# BEFORE
from app.core.crypto import encrypt_content, decrypt_content

# AFTER
from app.core.content_encryption import encrypt_content, decrypt_content
```

**Step 14.4 — Verify no remaining references to the old name:**
```bash
grep -r "core\.crypto\|core/crypto" backend/ --include="*.py"
# Should return nothing
```

**Step 14.5 — Run the full backend test suite:**
```bash
cd backend
pytest tests/ -v
```

---

**[COMMIT POINT]**
```
fix: resolve all 8 important audit issues

- add merge_projects to nsn/__init__.py re-exports
- fix token_savings update in retrieve() (was never written to project_meta)
- add episodic→semantic promotion phase to Celery sleep_engine.py
- add model_family default to nsn.init() config (Fix 3 follow-through)
- apply recall_threshold gating + miss logging to self-host recall() path
- fix Redis connection leak in /api/v1/health/deep → use app.state.redis
- remove hardcoded NSN_ENCRYPTION_MASTER_KEY default from docker-compose.yml
- rename core/crypto.py → core/content_encryption.py to eliminate ambiguity
```

---

## Phase 3 — Polish & Verification (🟢 Fixes 15–18)

These are verification tasks, not implementation. Work through them to confirm
the polish items are either done or clearly tracked.

---

### Fix 15 — Verify Miss Inspector Panel in Dashboard

**File:** `frontend/src/pages/Dashboard.tsx` (and surrounding pages/)

**What to check:**
- Open the running dashboard at `http://localhost:3000` (or `8080`)
- Navigate to every panel in the sidebar
- Confirm there is a **Miss Inspector** panel that shows:
  - A table of withheld memories
  - Columns: query text, score, threshold at time of miss, reason, timestamp
  - Clickable rows showing the full memory candidate that was withheld
  - Filterable by date range and score range

**If the panel exists but is incomplete:**
- Add the click-to-expand row detail
- Add date + score filters
- Wire it to `GET /api/v1/misses?project=...&limit=50&offset=0`

**If the panel is missing entirely:**
```
frontend/src/pages/
└── MissInspector.tsx     ← create this
```
```tsx
// MissInspector.tsx — minimum viable panel
// Fetches from GET /api/v1/misses
// Shows: query, score, threshold, reason, timestamp in a sortable table
// Row click expands to show full Memory object that was withheld
```
Add it to the sidebar navigation in `Sidebar.tsx`.

---

### Fix 16 — Verify `keygen` CLI Command

**File:** `sdk/python/neurosleepnet/cli.py`

**What to check — run the command in a clean environment:**
```bash
# In the Docker stack:
docker compose run --rm api python -m neurosleepnet.keygen

# Expected output (exactly this format):
# NeuroSleepNet API Key Generated
# ─────────────────────────────────────────────
# Key:  nsn_sk_<random>
# ─────────────────────────────────────────────
# This key is shown ONCE. Store it securely.
# The hash has been written to the database.
```

**What must be true:**
- Raw key printed once to stdout, never logged to file
- SHA256 hash written to `api_keys` table in PostgreSQL
- `key_prefix` (first 12 chars) also written (required for Fix 2)
- Running keygen a second time generates a new key AND marks the old one
  `rotated=true` in the database
- Old key is immediately rejected after rotation

**If any of the above is not true, fix `cli.py` and `keygen.py` accordingly.**

---

### Fix 17 — Verify Benchmark Harness is Runnable

**File:** `benchmarks/run_benchmark.py` (or `sdk/python/neurosleepnet/benchmark/`)

**What to check:**
```bash
python benchmarks/run_benchmark.py --help
# Should show available conditions and options
```

**Minimum for Checkpoint 6:**
```bash
python benchmarks/run_benchmark.py --condition phi3_nsn --sessions 10
# Should run 10 simulated sessions and print a score table
```

**If it fails or is incomplete, note exactly what is missing and add to the
Checkpoint 6 task tracker. Do not attempt to complete the full benchmark
harness here — that is its own checkpoint.**

---

### Fix 18 — Verify LangChain / LlamaIndex Adapter Stubs

**File:** `sdk/python/neurosleepnet/adapters/`

**What to check:**
```bash
ls sdk/python/neurosleepnet/adapters/
# Should have: langchain.py, llamaindex.py (or similar)

python -c "from neurosleepnet.adapters.langchain import NeuroSleepNetMemory"
# If ImportError → stub is broken even as a stub
```

**If they are stubs, they must at minimum:**
- Be importable without error
- Raise `NotImplementedError` with a message: `"NeuroSleepNetMemory is not
  yet implemented. Tracked in Checkpoint 7."`
- Be documented in the README as coming in Checkpoint 7

**This is not Checkpoint 7 work — it is just making sure the stubs don't
silently fail.**

---

**[COMMIT POINT]**
```
chore: verify and stabilize polish items (audit fixes 15-18)

- verify/complete Miss Inspector panel in dashboard
- verify keygen CLI: single print, hash stored, prefix stored, rotation works
- verify benchmark harness is runnable for at least one condition
- verify adapter stubs are importable and raise NotImplementedError cleanly
```

---

## Final Verification — Full Audit Pass

Run this after all three phases are complete. Every command should pass.

```bash
# 1. Clean install
cd sdk/python
pip install -e ".[dev]"
python -c "import nsn; print('alias ok')"
python -c "from nsn import merge_projects; print('merge_projects ok')"

# 2. SDK unit tests
pytest sdk/python/tests/ -v --tb=short

# 3. Stats + token savings
python -c "
import nsn
nsn.init(project='audit-final')
nsn.pin('Never give financial advice', label='disclaimer')
for i in range(5):
    nsn.remember(f'fact {i}', user_id='u1', type='episodic')
mems = nsn.recall('facts', user_id='u1', top_k=2)
s = nsn.stats()
assert s['token_savings_estimate'] > 0
assert s['pinned'] == 1
print('stats ok:', s)
"

# 4. model_family detection
python -c "
import nsn
nsn.init(project='mf-test', model_family='phi3')
ctx = nsn.context('test query', user_id='u1')
print('context ok, length:', len(ctx))
"

# 5. Docker stack
docker compose up -d
sleep 10

# 6. Health check returns real status
curl -s http://localhost:8080/health | python -m json.tool
# "db": "ok", "redis": "ok" — not hardcoded

# 7. Rate limit fires
for i in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer nsn_sk_dev_test" \
    http://localhost:8080/api/v1/stats)
  echo $CODE
done
# Should see 429 after the rate limit threshold

# 8. CORS — should NOT allow arbitrary origin with credentials
curl -s -I \
  -H "Origin: http://evil.example.com" \
  -H "Authorization: Bearer nsn_sk_test" \
  http://localhost:8080/api/v1/stats \
  | grep -i "access-control"
# Should NOT contain: Access-Control-Allow-Origin: *

# 9. Encryption key guard
NSN_ENCRYPTION_MASTER_KEY="changeme-in-production-32chars!!" \
  docker compose up api 2>&1 | grep "insecure"
# Should print the RuntimeError and refuse to start

# 10. Backend tests
cd backend
pytest tests/ -v --tb=short

# 11. keygen
docker compose run --rm api python -m neurosleepnet.keygen
# Should print nsn_sk_... once and exit

# 12. Self-host recall threshold gating
python -c "
import nsn
nsn.init(project='gate-test', mode='self-host',
         host='http://localhost:8080', api_key='your-key',
         recall_threshold=0.9)  # very high threshold
nsn.remember('completely unrelated topic', user_id='u1')
mems = nsn.recall('quantum physics', user_id='u1')
# All memories should be withheld (score below 0.9)
# miss_log should have an entry
s = nsn.stats()
print('miss_count:', s['miss_count'])  # should be > 0
"
```

---

> When all commands above pass without error, the audit is resolved.
> You are ready to move to Checkpoint 5.