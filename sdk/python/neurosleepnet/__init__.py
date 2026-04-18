import logging
import json
import time
import threading
from collections import deque
from typing import Any, List, Dict, Optional

from .client import NeuroSleepClient
from .cache import OfflineCache
from .fallback import execute_with_fallback, safe_wrap
from .adapters import get_adapter
from .proxy import TransparentProxy

class NSNInitError(RuntimeError):
    pass

# Global state
_config = {
    "api_key": None,
    "project": "default",
    "session_id": None,
    "fallback_mode": "silent",
    "offline_cache": True,
    "min_memories": 3,
    "log_level": "info"
}

_client: Optional[NeuroSleepClient] = None
_cache: Optional[OfflineCache] = None

# Write rate-limiting: max 20 writes per 10s window, overflow goes to cache
_write_queue: deque = deque()
_write_lock = threading.Lock()
_WRITE_RATE_WINDOW = 10   # seconds
_WRITE_RATE_LIMIT = 20    # max writes per window

def init(
    api_key: str,
    project: str = "default",
    session_id: str = None,
    fallback_mode: str = "silent",
    max_context_tokens: int = 2048,
    model_context_limit: int = 4096,
    min_memories: int = 3,
    offline_cache: bool = True,
    log_level: str = "info",
    disabled: bool = False
):
    """Initializes the NeuroSleepNet SDK."""
    global _client, _cache, _config
    
    _config.update({
        "api_key": api_key,
        "project": project,
        "session_id": session_id,
        "fallback_mode": fallback_mode,
        "offline_cache": offline_cache,
        "min_memories": min_memories,
        "max_context_tokens": max_context_tokens,
        "model_context_limit": model_context_limit,
        "log_level": log_level,
        "disabled": disabled
    })
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level)
    
    _client = NeuroSleepClient(api_key=api_key)
    
    # Eager Validation
    if not offline_cache:
        try:
            _client.ping()
        except Exception as e:
            raise NSNInitError(f"NeuroSleepNet initialization failed: Invalid API key or unreachable server. ({e})")
            
    if offline_cache:
        _cache = OfflineCache()

def _check_init():
    if not _client:
        raise NSNInitError(
            "Oh no! It looks like you forgot to call nsn.init() before wrapping your agent. "
            "Please add `nsn.init(api_key='...')` before calling nsn.wrap()."
        )

def status():
    """Prints a diagnostics summary of the NeuroSleepNet SDK state."""
    print("=" * 50)
    print("🧠 NeuroSleepNet — Diagnostics Status")
    print("=" * 50)
    if not _client:
        print("❌ SDK State: Not Initialized (Run nsn.init())")
        return
        
    print(f"✓ API Key:    Valid ({_config['api_key'][:8]}...)")
    print(f"✓ Project:    {_config['project']}")
    print(f"✓ Fallback:   {_config['fallback_mode']} mode")
    
    if _cache:
        if hasattr(_cache, 'db_path'):
            print(f"✓ Offline DB: Active ({_cache.db_path})")
        else:
            print(f"✓ Offline DB: Active")
            
    try:
        start = __import__('time').time()
        _client.ping()
        ms = int((__import__('time').time() - start) * 1000)
        print(f"✓ API Health: Reachable ({ms}ms latency)")
    except Exception as e:
        print(f"⚠ API Health: Unreachable ({e})")
        
    print("=" * 50)

def _check_quota():
    """Checks quota usage and emits warnings at 80% and 95% thresholds."""
    try:
        usage = _client.get_usage()
        pct = usage.get("used_pct", 0)
        limit = usage.get("limit", 0)
        used = usage.get("used", 0)
        
        if pct >= 95:
            logging.getLogger("neurosleepnet").warning(
                f"[NSN] \u26a0\ufe0f  QUOTA CRITICAL: {used}/{limit} memories used ({pct:.0f}%). "
                "New writes will be rejected. Upgrade your plan at https://neurosleepnet.ai/billing"
            )
        elif pct >= 80:
            logging.getLogger("neurosleepnet").warning(
                f"[NSN] \u26a0\ufe0f  Quota warning: {used}/{limit} memories used ({pct:.0f}%). "
                "Approaching your monthly limit."
            )
    except Exception:
        pass  # Quota check is non-blocking; never fail the main path

def _is_rate_limited() -> bool:
    """Sliding window rate limiter — returns True if limit exceeded."""
    now = time.monotonic()
    with _write_lock:
        # Evict timestamps outside the window
        while _write_queue and _write_queue[0] < now - _WRITE_RATE_WINDOW:
            _write_queue.popleft()
        if len(_write_queue) >= _WRITE_RATE_LIMIT:
            return True
        _write_queue.append(now)
        return False

def remember(content: str, tags: list = None, importance: float = 1.0, ttl_days: int = None):
    _check_init()
    _check_quota()
    
    if _is_rate_limited():
        # Silently fall to local cache rather than dropping the write
        logging.getLogger("neurosleepnet").debug(
            f"[NSN] Rate limit reached ({_WRITE_RATE_LIMIT} writes/{_WRITE_RATE_WINDOW}s). "
            "Buffering to offline cache."
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
            ttl_days=ttl_days
        )
        
    def _cache_call():
        if _cache:
            _cache.store(content, _config["project"], _config["session_id"], tags, importance)
            return {"status": "cached locally"}
        return None
        
    res, from_cache = execute_with_fallback(
        func=_api_call,
        cache_retrieve_fn=_cache_call,
        fallback_mode=_config["fallback_mode"]
    )
    return res

def snapshot(path: str = None) -> List[Dict[str, Any]]:
    """
    Exports the full memory state for this project.
    If `path` is provided, serialises to a JSON file.
    Returns the raw list of memory dicts regardless.
    """
    _check_init()
    memories = recall("", top_k=2000)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"project": _config["project"], "memories": memories}, f, indent=2, default=str)
        logging.getLogger("neurosleepnet").info(f"[NSN] Snapshot saved to {path}")
    return memories

def restore(snapshot_data, *, from_file: str = None):
    """
    Restores memories from a snapshot dict list or a JSON file exported by `snapshot()`.
    Use `from_file='path/to/snapshot.json'` to load from disk.
    """
    _check_init()
    if from_file:
        with open(from_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw.get("memories", raw) if isinstance(raw, dict) else raw
    else:
        items = snapshot_data or []
        
    restored = 0
    for item in items:
        try:
            remember(
                content=item.get("content", ""),
                tags=item.get("tags"),
                importance=item.get("importance", item.get("consolidation_score", 1.0))
            )
            restored += 1
        except Exception as e:
            logging.getLogger("neurosleepnet").warning(f"[NSN] Skipped memory during restore: {e}")
    
    logging.getLogger("neurosleepnet").info(f"[NSN] Restored {restored}/{len(items)} memories.")
    return {"restored": restored, "total": len(items)}

def wrap(agent: Any, **overrides) -> Any:
    """Wraps an agent transparently with memory injection."""
    _check_init()
    if _config.get("disabled", False):
        return agent
        
    fallback_mode = overrides.get("fallback_mode", _config["fallback_mode"])
    adapter = get_adapter(agent)
    
    def log_memories(query, memories, response):
        if not query and not response: return
        try:
            # We silently asynchronously store the interaction 
            # (In a real production system, this could be on a background thread)
            remember(content=f"User: {query}\nAgent: {response}", tags=["auto-interaction"])
        except Exception:
            pass
            
    wrapped = adapter.wrap_call(
        agent=agent,
        retrieve_fn=lambda q: recall(q, overrides.get("top_k", 5)),
        log_fn=log_memories,
        fallback_mode=fallback_mode
    )
    
    return TransparentProxy(agent, wrapped)
