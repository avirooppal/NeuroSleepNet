"""
NeuroSleepNet SDK — Public API

Required:
    nsn.init(project="my-agent")
    nsn.wrap(agent)

Optional:
    nsn.remember(content, importance=0.9)
    nsn.forget(query, older_than_days=30)
    nsn.recall(query, top_k=5)
    nsn.explain_last()
    nsn.status()
    nsn.snapshot()
    nsn.restore(snapshot)
    nsn.trigger_sleep()
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

from .local_store import LocalStore
from .embeddings import EmbeddingManager
from .local_sleep import LocalSleepEngine


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class NSNAuthError(RuntimeError): pass
class NSNConnectionError(RuntimeError): pass
class NSNInitError(RuntimeError): pass


# ── Global State ───────────────────────────────────────────────────────────────

_config: Dict[str, Any] = {
    "mode": "local",  # "local" | "server" | "cloud"
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
    "data_dir": "~/.neurosleepnet",
    "embeddings": "local",
    "min_confidence": 0.35,  # Hard threshold: don't guess if below this
}

# Server/Cloud mode state
_client: Optional[NeuroSleepClient] = None
_cache: Optional[OfflineCache] = None

# Local mode state
_local_store: Optional[LocalStore] = None
_embedding_manager: Optional[EmbeddingManager] = None
_local_sleep: Optional[LocalSleepEngine] = None

_last_retrieval: Dict[str, Any] = {}   # Stores context for explain_last()
_detected_adapter_name: str = "Unknown"

# Write rate-limiting: max 20 writes per 10s sliding window
_write_queue: deque = deque()
_write_lock = threading.Lock()
_WRITE_RATE_WINDOW = 10
_WRITE_RATE_LIMIT = 20


# ── init() ─────────────────────────────────────────────────────────────────────

def init(
    project: str = "default",
    mode: str = "local",                 # "local" | "server" | "cloud"
    api_key: Optional[str] = None,       # Optional for local, required for server/cloud
    session_id: Optional[str] = None,
    base_url: Optional[str] = None,      # For server mode
    data_dir: str = "~/.neurosleepnet",  # Local storage path
    embeddings: str = "local",           # "local" | "openai" | "none"
    embedding_model: Optional[str] = None,
    sleep_interval_hours: float = 6.0,   # Local sleep consolidation frequency
    fallback_mode: str = "silent",       # "silent" | "warn" | "raise"
    max_context_tokens: int = 2048,
    min_memories: int = 3,
    model_context_limit: Optional[int] = None,
    offline_cache: bool = True,
    pii_detection: bool = True,
    memory_ttl_days: Optional[int] = None,
    filter_fn: Optional[Callable] = None,
    telemetry: bool = False,
    log_level: str = "info",
    disabled: bool = False,
):
    """
    Initialize the NeuroSleepNet SDK.
    Call once at application startup.
    """
    global _client, _cache, _local_store, _embedding_manager, _local_sleep, _config

    _config.update({
        "mode": mode,
        "api_key": api_key,
        "project": project,
        "session_id": session_id or str(_uuid.uuid4()),
        "data_dir": data_dir,
        "embeddings": embeddings,
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
    logger = logging.getLogger("neurosleepnet")

    if mode == "local":
        _local_store = LocalStore(data_dir=data_dir)
        _embedding_manager = EmbeddingManager(provider=embeddings, model_name=embedding_model, api_key=api_key)
        _local_sleep = LocalSleepEngine(_local_store, interval_hours=sleep_interval_hours)
        _local_sleep.start()
        print(f"\\n[NSN] NeuroSleepNet Initialized (Local Mode) - Project: {project}\\n")

    elif mode in ("server", "cloud"):
        if not api_key and mode == "cloud":
            logger.warning("[NSN] api_key not provided, using 'anonymous'")
            api_key = "anonymous"
            
        kwargs = {"api_key": api_key or "anonymous"}
        if base_url:
            kwargs["base_url"] = base_url
            
        _client = NeuroSleepClient(**kwargs)

        if offline_cache:
            _cache = OfflineCache()

        try:
            projects = _client.list_projects()
            existing = next((p for p in projects if p["name"] == project), None)
            if existing:
                _config["project"] = existing["id"]
            else:
                try:
                    new_p = _client.create_project(project)
                    _config["project"] = new_p["id"]
                except Exception as e:
                    logger.warning(f"Failed to auto-create project '{project}' via API: {e}. Falling back to name-based ID.")
                    _config["project"] = project
        except Exception as e:
            logger.warning(f"Could not reach API to resolve project '{project}': {e}. Proceeding with name-based ID.")
            _config["project"] = project

        print(f"\\n[NSN] NeuroSleepNet Initialized! View your live metrics at: http://localhost:3000/dashboard/{_config['project']}\\n")

    else:
        raise ValueError(f"Unknown mode: {mode}")


# ── Internal helpers ───────────────────────────────────────────────────────────

def _check_init():
    if _config["mode"] == "local" and not _local_store:
        raise NSNInitError("nsn.init() must be called before making requests.")
    elif _config["mode"] in ("server", "cloud") and not _client:
        raise NSNInitError("nsn.init() must be called before making requests.")

def _is_rate_limited() -> bool:
    now = time.monotonic()
    with _write_lock:
        while _write_queue and _write_queue[0] < now - _WRITE_RATE_WINDOW:
            _write_queue.popleft()
        if len(_write_queue) >= _WRITE_RATE_LIMIT:
            return True
        _write_queue.append(now)
        return False


# ── Public API ─────────────────────────────────────────────────────────────────

def remember(
    content: str,
    importance: float = 1.0,
    tags: Optional[List[str]] = None,
    ttl_days: Optional[int] = None,
):
    _check_init()

    if _config.get("disabled"):
        return None

    ttl = ttl_days or _config.get("memory_ttl_days")

    if _config["mode"] == "local":
        try:
            emb = _embedding_manager.embed_single(content)
            memory_id = _local_store.store(
                content=content, 
                project=_config["project"],
                session_id=_config["session_id"],
                tags=tags or [],
                importance=importance,
                embedding=emb,
                ttl_days=ttl
            )
            return {"status": "stored_locally", "id": memory_id}
        except Exception as e:
            if _config["fallback_mode"] == "raise":
                raise
            logging.getLogger("neurosleepnet").warning(f"[NSN] Local remember failed: {e}")
            return None

    else: # server/cloud
        if _is_rate_limited():
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
    _check_init()
    if _config.get("disabled"):
        return []

    if _config["mode"] == "local":
        try:
            q_emb = _embedding_manager.embed_single(query)
            if q_emb:
                # Pass both query string and embedding for Hybrid Search
                memories = _local_store.retrieve(query, q_emb, _config["project"], top_k=top_k)
                # Filter by hard confidence threshold
                memories = [m for m in memories if m.get("attention_score", 0) >= _config["min_confidence"]]
            else:
                memories = _local_store.search_text(query, _config["project"], top_k=top_k)
            from_cache = False
        except Exception as e:
            logging.getLogger("neurosleepnet").warning(f"[NSN] Local recall failed: {e}")
            memories = []
            from_cache = False
    else:
        def _api_call():
            return _client.retrieve(
                query=query,
                project=_config["project"],
                top_k=top_k,
            )

        def _cache_call():
            if _cache:
                return _cache.retrieve(_config["project"], limit=top_k)
            return []

        memories, from_cache = execute_with_fallback(
            func=_api_call,
            cache_retrieve_fn=_cache_call,
            fallback_mode=_config["fallback_mode"],
        )

    global _last_retrieval
    _last_retrieval = {
        "query": query,
        "memories": memories,
        "from_cache": from_cache,
        "timestamp": time.time()
    }
    return memories


def forget(
    query: str,
    older_than_days: Optional[int] = None,
):
    _check_init()
    if _config.get("disabled"):
        return None

    if _config["mode"] == "local":
        try:
            deleted = _local_store.forget(query=query, older_than_days=older_than_days, project=_config["project"])
            return {"deleted": deleted}
        except Exception as e:
            if _config["fallback_mode"] == "raise":
                raise
            logging.getLogger("neurosleepnet").warning(f"[NSN] Local forget failed: {e}")
            return None
    else:
        try:
            return _client.forget(
                query=query,
                older_than_days=older_than_days,
            )
        except Exception as e:
            if _config["fallback_mode"] == "raise":
                raise
            logging.getLogger("neurosleepnet").warning(f"[NSN] forget() failed: {e}")
            return None


def explain_last() -> Dict[str, Any]:
    _check_init()
    if not _last_retrieval:
        return {"explanation": "No retrieval has occurred yet in this session."}

    memories = _last_retrieval.get("memories", [])
    return {
        "query": _last_retrieval.get("query", ""),
        "retrieved_at": _last_retrieval.get("timestamp"),
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


def trigger_sleep():
    """Manually trigger memory consolidation."""
    _check_init()
    if _config["mode"] == "local":
        return _local_sleep.run_now()
    else:
        return _client.trigger_sleep(_config["project"])


def status():
    WIDTH = 50
    SEP = "-" * WIDTH

    print(f"\\nNeuroSleepNet - System Status")
    print(SEP)

    if _config["mode"] == "local":
        if not _local_store:
            print("[!] SDK not initialized. Run nsn.init() first.")
            print(SEP)
            return
            
        print(f"[v] Mode           local")
        print(f"[v] Storage        {_local_store.db_path}")
        print(f"[v] Embeddings     {_config['embeddings']} ({_embedding_manager.model_name})")
        print(f"[v] Sleep Thread   {'running' if _local_sleep and _local_sleep._thread and _local_sleep._thread.is_alive() else 'stopped'}")
    else:
        if not _client:
            print("[!] SDK not initialized. Run nsn.init() first.")
            print(SEP)
            return

        key = _config.get("api_key", "")
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key[:4] + "..."
        print(f"[v] Mode           {_config['mode']}")
        print(f"[v] API key        valid  ({masked})")

        try:
            t0 = time.time()
            _client.ping()
            ms = int((time.time() - t0) * 1000)
            print(f"[v] API reachable  {ms}ms   ({_client.base_url})")
        except Exception as e:
            print(f"[!] API reachable  UNREACHABLE ({e})")

        if _cache:
            print(f"[v] Offline cache  active")
        else:
            print("[-] Offline cache  disabled")

    print("-" * 50)
    print(f"    Project        {_config['project']}")
    print(f"    Session        {_config.get('session_id', 'n/a')[:8]}")
    print(f"    Adapter        {_detected_adapter_name}")
    print(f"    Fallback mode  {_config.get('fallback_mode', 'silent')}")
    print(SEP)
    print()


def snapshot(path: Optional[str] = None) -> List[Dict[str, Any]]:
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
    global _detected_adapter_name
    _check_init()

    if _config.get("disabled"):
        return agent

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
            mems = recall(query, top_k=top_k)
            # Add temporal context to the content
            now = datetime.now(timezone.utc)
            for m in mems:
                try:
                    created = datetime.strptime(m["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    diff = now - created
                    if diff.days == 0:
                        label = "just now" if diff.seconds < 3600 else f"{diff.seconds // 3600}h ago"
                    else:
                        label = f"{diff.days}d ago"
                    m["content"] = f"[Memory ({label})]: {m['content']}"
                except: pass
            return mems
        except Exception:
            return []

    def _log(query: str, memories: List, response: str):
        if not query and not response:
            return
        try:
            content = f"User: {query}\\nAgent: {response}" if query else f"Agent: {response}"
            remember(content=content, tags=["auto-interaction"])
        except Exception:
            pass

    augmented = adapter.wrap_call(
        agent=agent,
        retrieve_fn=_retrieve,
        log_fn=_log,
        fallback_mode=fallback_mode,
        model_context_limit=model_limit,
    )

    return TransparentProxy(agent, augmented)
