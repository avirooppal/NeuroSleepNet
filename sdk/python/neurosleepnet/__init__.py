"""
NeuroSleepNet SDK — Public API

Required:
    nsn.init(api_key)     — call once at application startup
    nsn.wrap(agent)       — call once per agent, drop-in replacement

Optional:
    nsn.remember(content, importance=0.9)
    nsn.forget(query, older_than_days=30)
    nsn.recall(query, top_k=5)
    nsn.explain_last()
    nsn.status()
    nsn.snapshot()
    nsn.restore(snapshot)
"""
import json
import logging
import time
import threading
import uuid as _uuid
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .client import NeuroSleepClient
from .cache import OfflineCache
from .fallback import execute_with_fallback
from .adapters import get_adapter
from .proxy import TransparentProxy
from .context import get_model_context_limit


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class NSNAuthError(RuntimeError):
    """Raised when the API key is invalid — detected eagerly at nsn.init()."""

class NSNConnectionError(RuntimeError):
    """Raised when the API is unreachable and fallback_mode='raise'."""

class NSNInitError(RuntimeError):
    """Raised when nsn.wrap() or other operations are called before nsn.init()."""


# ── Global State ───────────────────────────────────────────────────────────────

_config: Dict[str, Any] = {
    "api_key": None,
    "project": "default",
    "session_id": None,
    "fallback_mode": "silent",
    "max_context_tokens": 2048,
    "model_context_limit": None,
    "min_memories": 3,
    "offline_cache": True,
    "pii_detection": True,
    "memory_ttl_days": None,
    "filter_fn": None,
    "telemetry": False,
    "log_level": "info",
    "disabled": False,
}

_client: Optional[NeuroSleepClient] = None
_cache: Optional[OfflineCache] = None
_last_retrieval: Dict[str, Any] = {}   # Stores context for explain_last()
_detected_adapter_name: str = "Unknown"

# Write rate-limiting: max 20 writes per 10s sliding window
_write_queue: deque = deque()
_write_lock = threading.Lock()
_WRITE_RATE_WINDOW = 10
_WRITE_RATE_LIMIT = 20


# ── init() ─────────────────────────────────────────────────────────────────────

def init(
    api_key: str,
    project: str = "default",
    session_id: Optional[str] = None,
    fallback_mode: str = "silent",       # "silent" | "warn" | "raise"
    max_context_tokens: int = 2048,
    min_memories: int = 3,
    model_context_limit: Optional[int] = None,
    offline_cache: bool = True,
    pii_detection: bool = True,          # DEFAULT ON. False = conscious opt-out.
    memory_ttl_days: Optional[int] = None,
    filter_fn: Optional[Callable] = None,
    telemetry: bool = False,             # NEVER default True.
    log_level: str = "info",
    disabled: bool = False,
):
    """
    Initialize the NeuroSleepNet SDK.

    Call once at application startup. Immediately validates the API key via
    GET /v1/ping — fail fast, never surface a bad key 10 minutes into a run.

    Args:
        api_key:             Required. Validated immediately via ping.
        project:             Namespace. Memories scoped to project.
        session_id:          Auto-generated UUID if not provided.
        fallback_mode:       "silent" | "warn" | "raise"
        max_context_tokens:  Hard cap on injected memory size per call.
        min_memories:        Sleep engine never prunes below this floor.
        model_context_limit: Override model's max context window (tokens).
        offline_cache:       SQLite fallback at ~/.nsn/cache.db
        pii_detection:       ON BY DEFAULT. False = conscious opt-out.
        memory_ttl_days:     Hard deletion after N days. None = no expiry.
        filter_fn:           Custom callable: filter_fn(content) -> bool
        telemetry:           Opt-in only. Never sends memory content.
        log_level:           "debug" | "info" | "warn" | "none"
        disabled:            Kill-switch. Used for benchmark control groups.
    """
    global _client, _cache, _config

    if not api_key:
        raise NSNAuthError("api_key is required. Get yours at nsn.ai/dashboard/keys.")

    _config.update({
        "api_key": api_key,
        "project": project,
        "session_id": session_id or str(_uuid.uuid4()),
        "fallback_mode": fallback_mode,
        "max_context_tokens": max_context_tokens,
        "model_context_limit": model_context_limit,
        "min_memories": min_memories,
        "offline_cache": offline_cache,
        "pii_detection": pii_detection,
        "memory_ttl_days": memory_ttl_days,
        "filter_fn": filter_fn,
        "telemetry": telemetry,
        "log_level": log_level,
        "disabled": disabled,
    })

    # Configure logging
    level_map = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARNING, "none": logging.CRITICAL + 1}
    logging.basicConfig(level=level_map.get(log_level, logging.INFO))

    _client = NeuroSleepClient(api_key=api_key)

    if offline_cache:
        _cache = OfflineCache()

    # ── Eager key validation (locked contract) ───────────────────────────────
    # Valid key    → proceeds silently
    # Invalid key  → raises NSNAuthError immediately
    # Network down → respects fallback_mode
    try:
        _client.ping()
    except Exception as e:
        err_str = str(e).lower()
        is_auth_error = any(k in err_str for k in ["401", "403", "unauthorized", "forbidden", "invalid"])
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key[:4] + "..."

        if is_auth_error:
            raise NSNAuthError(
                f"Invalid API key '{masked_key}'. Check your key at nsn.ai/dashboard/keys."
            )
        # Network down — respects fallback_mode
        if fallback_mode == "raise":
            raise NSNConnectionError(
                f"NeuroSleepNet API unreachable. Check your connection or api.nsn.ai status. ({e})"
            )
        elif fallback_mode == "warn":
            logging.getLogger("neurosleepnet").warning(
                f"[NSN] API unreachable at init — running in offline mode. ({e})"
            )
        # fallback_mode="silent" → no output


# ── Internal helpers ───────────────────────────────────────────────────────────

def _check_init():
    if not _client:
        raise NSNInitError(
            "nsn.init() must be called before nsn.wrap().\n"
            "Add nsn.init('your_key') at application startup."
        )

def _is_rate_limited() -> bool:
    """Sliding window rate limiter — returns True if limit exceeded."""
    now = time.monotonic()
    with _write_lock:
        while _write_queue and _write_queue[0] < now - _WRITE_RATE_WINDOW:
            _write_queue.popleft()
        if len(_write_queue) >= _WRITE_RATE_LIMIT:
            return True
        _write_queue.append(now)
        return False

def _check_quota():
    """Quota check — fires warnings at 80% and 95%. Never blocks main path."""
    try:
        usage = _client.get_usage()
        pct = usage.get("used_pct", 0)
        limit = usage.get("limit", 0)
        used = usage.get("used", 0)
        log = logging.getLogger("neurosleepnet")
        if pct >= 95:
            log.warning(f"[NSN] ⚠️ QUOTA CRITICAL: {used}/{limit} ({pct:.0f}%). Upgrade at nsn.ai/billing")
        elif pct >= 80:
            log.warning(f"[NSN] ⚠️ Quota warning: {used}/{limit} ({pct:.0f}%). Approaching monthly limit.")
    except Exception:
        pass


# ── Public API ─────────────────────────────────────────────────────────────────

def remember(
    content: str,
    importance: float = 1.0,
    tags: Optional[List[str]] = None,
    ttl_days: Optional[int] = None,
):
    """
    Manually store a memory with optional importance weighting.
    High importance memories resist sleep-phase archival.
    """
    _check_init()
    _check_quota()

    if _config.get("disabled"):
        return None

    ttl = ttl_days or _config.get("memory_ttl_days")

    if _is_rate_limited():
        logging.getLogger("neurosleepnet").debug(
            f"[NSN] Rate limit reached ({_WRITE_RATE_LIMIT}/{_WRITE_RATE_WINDOW}s). Buffering to cache."
        )
        if _cache:
            _cache.store(content, _config["project"], _config["session_id"], tags, importance)
            return {"status": "rate_limited_cached_locally"}
        return None

    def _api_call():
        return _client.store_memory(
            content=content,
            project=_config["project"],
            tags=tags or [],
            importance=importance,
            session_id=_config["session_id"],
            ttl_days=ttl,
        )

    def _cache_call():
        if _cache:
            _cache.store(content, _config["project"], _config["session_id"], tags, importance)
            return {"status": "cached_locally"}
        return None

    res, _ = execute_with_fallback(
        func=_api_call,
        cache_retrieve_fn=_cache_call,
        fallback_mode=_config["fallback_mode"],
    )
    return res


def recall(
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant memories for a query.
    Uses semantic search + attention reranking.
    """
    _check_init()
    if _config.get("disabled"):
        return []

    try:
        result = _client.search_memories(
            query=query,
            project=_config["project"],
            session_id=_config["session_id"],
            top_k=top_k,
        )
        memories = result if isinstance(result, list) else result.get("memories", [])

        # Update last retrieval context for explain_last()
        global _last_retrieval
        _last_retrieval = {
            "query": query,
            "memories": memories,
            "retrieved_at": time.time(),
        }
        return memories
    except Exception as e:
        if _config["fallback_mode"] == "raise":
            raise
        if _cache:
            return _cache.retrieve(query, _config["project"], top_k)
        return []


def forget(
    query: str,
    older_than_days: Optional[int] = None,
):
    """
    Semantically forget all memories matching the query.
    Optionally filter to memories older than N days.

    Example:
        nsn.forget("auth module bug", older_than_days=30)
    """
    _check_init()
    if _config.get("disabled"):
        return None

    try:
        return _client.forget_by_query(
            query=query,
            project=_config["project"],
            older_than_days=older_than_days,
        )
    except Exception as e:
        if _config["fallback_mode"] == "raise":
            raise
        logging.getLogger("neurosleepnet").warning(f"[NSN] forget() failed: {e}")
        return None


def explain_last() -> Dict[str, Any]:
    """
    Explain why specific memories were retrieved in the last agent call.
    Returns the query used, the memories returned, and their attention scores.

    Example output:
        {
          "query": "what did the user say about performance?",
          "retrieved_at": 1718...,
          "memories": [...],
          "why": "Memories ranked by attention score = CosineSim×0.5 + Recency×0.2 + ..."
        }
    """
    _check_init()
    if not _last_retrieval:
        return {"explanation": "No retrieval has occurred yet in this session."}

    memories = _last_retrieval.get("memories", [])
    return {
        "query": _last_retrieval.get("query", ""),
        "retrieved_at": _last_retrieval.get("retrieved_at"),
        "memories": memories,
        "count": len(memories),
        "why": (
            "Memories ranked by AttentionScore = "
            "(CosineSimilarity × 0.50) + (Recency × 0.20) + "
            "(ConsolidationScore × 0.20) + (ImportanceBoost × 0.10)"
        ),
        "attention_scores": [
            round(m.get("attention_score", m.get("consolidation_score", 0.0)), 4)
            for m in memories
        ],
    }


def status():
    """
    Print a full system diagnostics summary to stdout.

    Format (locked):
    ──────────────────────────────────────────────────
    ✓  API key        valid  (nsn_...a3f2)
    ✓  API reachable  43ms   (api.nsn.ai)
    ...
    ──────────────────────────────────────────────────
    """
    WIDTH = 50
    SEP = "─" * WIDTH

    print(f"\nNeuroSleepNet — System Status")
    print(SEP)

    if not _client:
        print("❌  SDK not initialized. Run nsn.init('your_key') first.")
        print(SEP)
        return

    key = _config.get("api_key", "")
    masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key[:4] + "..."
    print(f"✓   API key        valid  ({masked})")

    # API reachability
    try:
        t0 = time.time()
        _client.ping()
        ms = int((time.time() - t0) * 1000)
        print(f"✓   API reachable  {ms}ms   (api.nsn.ai)")
    except Exception as e:
        print(f"⚠   API reachable  UNREACHABLE ({e})")

    # Offline cache
    if _cache:
        cache_info = getattr(_cache, 'db_path', '~/.nsn/cache.db')
        try:
            count = _cache.count(_config["project"])
            print(f"✓   Offline cache  active ({cache_info} · {count} memories)")
        except Exception:
            print(f"✓   Offline cache  active ({cache_info})")
    else:
        print("─   Offline cache  disabled")

    # Quota
    try:
        usage = _client.get_usage()
        used = usage.get("used", 0)
        limit = usage.get("limit", 0)
        pct = usage.get("used_pct", 0)
        symbol = "⚠" if pct >= 80 else "✓"
        print(f"{symbol}   Quota          {pct:.0f}% used ({used:,} / {limit:,} calls this month)")
    except Exception:
        print("─   Quota          unavailable")

    print("─")
    print(f"    Project        {_config['project']}")
    print(f"    Session        {_config.get('session_id', 'n/a')[:8]}")
    print(f"    Adapter        {_detected_adapter_name}")
    print(f"    PII detection  {'enabled' if _config.get('pii_detection', True) else 'DISABLED (opt-out)'}")
    ttl = _config.get("memory_ttl_days")
    print(f"    Memory TTL     {f'{ttl} days' if ttl else 'none (no expiry)'}")
    print(f"    Fallback mode  {_config.get('fallback_mode', 'silent')}")
    print(SEP)
    print()


def snapshot(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Export the full memory state for this project.
    If path is provided, serialises to a JSON file.

    Use case: staging → prod migration, test fixtures.
    """
    _check_init()
    memories = recall("", top_k=2000)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"project": _config["project"], "memories": memories},
                f, indent=2, default=str,
            )
        logging.getLogger("neurosleepnet").info(f"[NSN] Snapshot saved to {path}")
    return memories


def restore(
    snapshot_data: Optional[List[Dict]] = None,
    *,
    from_file: Optional[str] = None,
):
    """
    Restore memories from a snapshot dict list or a JSON file exported by snapshot().

    Example:
        snap = nsn.snapshot()
        nsn.restore(snap)
        # or
        nsn.restore(from_file="backup.json")
    """
    _check_init()

    if from_file:
        with open(from_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw.get("memories", raw) if isinstance(raw, dict) else raw
    else:
        items = snapshot_data or []

    log = logging.getLogger("neurosleepnet")
    restored = 0
    for item in items:
        try:
            remember(
                content=item.get("content", ""),
                tags=item.get("tags"),
                importance=item.get("importance", item.get("consolidation_score", 1.0)),
            )
            restored += 1
        except Exception as e:
            log.warning(f"[NSN] Skipped memory during restore: {e}")

    log.info(f"[NSN] Restored {restored}/{len(items)} memories.")
    return {"restored": restored, "total": len(items)}


def wrap(agent: Any, **overrides) -> Any:
    """
    Wrap an agent transparently with memory injection.

    The wrapped agent is a transparent proxy:
      - isinstance(wrapped, OriginalClass) → True
      - wrapped.__class__.__name__ matches original
      - All call signatures preserved

    Must be called AFTER nsn.init().
    """
    global _detected_adapter_name

    _check_init()

    if _config.get("disabled"):
        return agent  # Control group — return original untouched

    fallback_mode = overrides.get("fallback_mode", _config["fallback_mode"])
    model_limit = overrides.get(
        "model_context_limit",
        _config.get("model_context_limit") or get_model_context_limit("")
    )
    top_k = overrides.get("top_k", 5)

    adapter = get_adapter(agent)
    _detected_adapter_name = type(adapter).__name__

    def _retrieve(query: str):
        try:
            return recall(query, top_k=top_k)
        except Exception:
            return []

    def _log(query: str, memories: List, response: str):
        """Store the full interaction as a memory."""
        if not query and not response:
            return
        try:
            content = f"User: {query}\nAgent: {response}" if query else f"Agent: {response}"
            remember(content=content, tags=["auto-interaction"])
        except Exception:
            pass

    # Let adapter wrap the agent
    augmented = adapter.wrap_call(
        agent=agent,
        retrieve_fn=_retrieve,
        log_fn=_log,
        fallback_mode=fallback_mode,
        model_context_limit=model_limit,
    )

    return TransparentProxy(agent, augmented)
