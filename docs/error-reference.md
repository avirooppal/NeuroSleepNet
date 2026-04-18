# SDK Error Reference — Common Failure Modes

Every error NSN can raise, what caused it, and how to fix it.

---

## `NSNInitError` — Not Initialized

```
NSNInitError: Oh no! It looks like you forgot to call nsn.init() before wrapping your agent.
Please add `nsn.init(api_key='...')` before calling nsn.wrap().
```

**Cause:** `nsn.wrap()`, `nsn.remember()`, or `nsn.recall()` was called before `nsn.init()`.

**Fix:**
```python
import neurosleepnet as nsn

nsn.init(api_key="your_key")          # ← must come first
agent = nsn.wrap(your_agent)
```

---

## `NSNInitError` — Invalid API Key / Server Unreachable

```
NSNInitError: NeuroSleepNet initialization failed: Invalid API key or unreachable server. (...)
```

**Cause:** `nsn.init()` performed an eager ping to `/v1/ping` and received a non-200 response.

**Possible causes:**
- API key is wrong, expired, or has no project assigned
- Backend URL is incorrect (self-hosted deployments)
- Network firewall blocking outbound HTTPS

**Fix:**
```python
# Option A — fix your key
nsn.init(api_key="correct_key_here")

# Option B — use offline-only mode during development (skips ping)
nsn.init(api_key="any_key", offline_cache=True)
```

---

## Silent Rate Limit (writes buffered to local cache)

```
[NSN] Rate limit reached (20 writes/10s). Buffering to offline cache.
```

**Cause:** More than 20 `nsn.remember()` calls fired within a 10-second window. NSN silently buffers extras to the local SQLite cache rather than dropping them.

**This is not an error** — it is a safety behaviour. Your data is not lost.

**Fix:** If you are bulk-importing, use the batch API instead:
```python
import httpx

client = httpx.Client(headers={"Authorization": f"Bearer {api_key}"})
client.post("/v1/memories/batch", json=[
    {"content": "...", "project_id": "..."} for _ in range(100)
])
```

---

## Quota Warning — 80% / 95% Usage

```
[NSN] ⚠️  Quota warning: 8000/10000 memories used (80%). Approaching your monthly limit.
[NSN] ⚠️  QUOTA CRITICAL: 9500/10000 memories used (95%). New writes will be rejected.
```

**Cause:** Your project is approaching its memory quota.

**Fix:** Either:
- Use `nsn.forget(query="...")` to prune stale memories
- Upgrade your plan at `https://neurosleepnet.ai/billing`
- Use `ttl_days=N` on `nsn.remember()` to auto-expire transient memories

---

## `isinstance()` check passes but agent behaviour is wrong

**Cause:** The `TransparentProxy` wraps all attribute access, but if the agent has classmethods or `@staticmethod` calls that go through `type()` rather than the instance, they may behave unexpectedly.

**Fix:** Access the underlying agent via `agent.__wrapped__` for classmethods:
```python
wrapped = nsn.wrap(my_agent)
result = wrapped.__wrapped__.some_classmethod()
```

---

## Streaming response only partially logged

**Cause:** If you consume *part* of a generator and then discard it, NSN's stream proxy never reaches the `log_fn` call at the end of the generator.

**Fix:** Always exhaust the generator if you want logging:
```python
for chunk in nsn_agent("What is X?"):
    print(chunk, end="", flush=True)
# ← logging fires here, after the final chunk
```

---

## HuggingFace pipeline returns unexpected structure

```
[NSN] HuggingFace Pipeline wrapper error: 'list' object has no attribute 'get'
```

**Cause:** Some HuggingFace pipelines return nested lists rather than a flat `[{"generated_text": "..."}]`.

**Fix:** The `HuggingFaceAdapter.extract_response()` handles this, but if you use a custom pipeline task, extend the adapter:
```python
from neurosleepnet.adapters.huggingface import HuggingFaceAdapter

class MyAdapter(HuggingFaceAdapter):
    def extract_response(self, response):
        return response[0][0]["generated_text"]
```

---

## Context window warning: dropping memories

```
WARNING: Dropping memory due to context window bounds (limit: 4096)
```

**Cause:** The total tokens of injected memories plus the user query exceeded `model_context_limit`.

**Fix:** Either increase the limit during `nsn.init()`, or reduce the number of retrieved memories:
```python
nsn.init(api_key="...", model_context_limit=8192)
# or
nsn.wrap(agent, top_k=3, model_context_limit=2048)
```

---

## `AES decrypt` fails on old memories

**Cause:** Pre-encryption memories stored before enabling `NSN_ENCRYPTION_KEY` cannot be decrypted and are served as-is. This is the intended graceful fallback.

**To re-encrypt old plaintext memories:** Export via `nsn.snapshot()`, delete all memories, and `nsn.restore()` — the restore path will encrypt on write.
