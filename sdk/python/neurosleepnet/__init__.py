"""
NeuroSleepNet SDK — Public API

Quick start:
    import nsn
    nsn.init(project="my-agent")
    agent = nsn.wrap(your_slm)

Or equivalently:
    import neurosleepnet as nsn
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import threading
import time
import uuid as _uuid
import webbrowser
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, List, Optional, Union

# ── Model family detection ─────────────────────────────────────────────────────

_MODEL_FAMILY_MAP: Dict[str, str] = {
    "phi":     "phi3",
    "mistral": "mistral",
    "gemma":   "gemma",
    "llama":   "llama3",
}

def _detect_model_family(model_name: str) -> str:
    """Map a model name string to a context.py model_family key."""
    if not model_name:
        return "generic"
    name = model_name.lower()
    for key, family in _MODEL_FAMILY_MAP.items():
        if key in name:
            return family
    return "generic"

from .context import (
    build_context,
    classify_model_strength,
    get_model_context_limit,
    get_recommended_settings,
    safe_inject,
    estimate_tokens,
)
from .local_store import LocalStore
from .local_sleep import LocalSleepEngine
from .embeddings import EmbeddingManager
from .feedback import apply_implicit_feedback
from . import dashboard as _dashboard_mod

__all__ = [
    "init", "wrap", "remember", "recall",
    "forget", "forget_user", "forget_project",
    "pin", "unpin", "list_pins",
    "feedback", "feedback_batch",
    "sleep", "sleep_status", "sleep_pause", "sleep_resume",
    "list_memories", "search", "stats",
    "export", "import_memories", "merge_projects",
    "dashboard", "context", "get_embed",
    "NSNAuthError", "NSNConnectionError", "NSNInitError",
]

# ── Exceptions ─────────────────────────────────────────────────────────────────

class NSNAuthError(RuntimeError): pass
class NSNConnectionError(RuntimeError): pass
class NSNInitError(RuntimeError): pass

# ── Global state ───────────────────────────────────────────────────────────────

_config: Dict[str, Any] = {}
_local_store: Optional[LocalStore] = None
_embed: Optional[EmbeddingManager] = None
_sleep_engine: Optional[LocalSleepEngine] = None
_last_recalled: List[Dict] = []
_initialized = False

_logger = logging.getLogger("neurosleepnet")


# ── init() ─────────────────────────────────────────────────────────────────────

def init(
    project: str = "default",
    mode: str = "local",
    # self-host
    host: Optional[str] = None,
    api_key: Optional[str] = None,
    # memory behaviour
    memory_window: int = 4096,
    sleep_interval: int = 300,
    sleep_on_exit: bool = True,
    embed_model: str = "local",
    recall_threshold: float = 0.6,
    implicit_feedback: bool = True,
    decay: bool = True,
    # Fix 3: project-level model family default used by wrap() and context()
    model_family: str = "generic",
    debug: bool = False,
    # extra
    data_dir: str = "~/.neurosleepnet",
    embedding_model: Optional[str] = None,
):
    """Initialize NeuroSleepNet. Call once at startup."""
    global _config, _local_store, _embed, _sleep_engine, _initialized

    log_level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=log_level)
    _logger.setLevel(log_level)

    _config = {
        "project": project,
        "mode": mode,
        "host": host or "http://localhost:8080/api",
        "api_key": api_key,
        "memory_window": memory_window,
        "sleep_interval": sleep_interval,
        "sleep_on_exit": sleep_on_exit,
        "embed_model": embed_model,
        "recall_threshold": recall_threshold,
        "implicit_feedback": implicit_feedback,
        "decay": decay,
        "model_family": model_family,   # Fix 3: stored for use in wrap() + context()
        "debug": debug,
        "data_dir": data_dir,
        "embedding_model": embedding_model,
        "session_id": str(_uuid.uuid4()),
    }

    if mode == "local":
        _local_store = LocalStore(data_dir=data_dir)
        _embed = EmbeddingManager(
            provider=embed_model,
            model_name=embedding_model,
            api_key=api_key,
        )
        _sleep_engine = LocalSleepEngine(
            store=_local_store,
            project=project,
            interval_seconds=float(sleep_interval),
            sleep_on_exit=sleep_on_exit,
        )
        _sleep_engine.start()

        first_run = _local_store._is_first_run(project)
        _local_store.mark_seen(project)

        # Start local dashboard server
        db_path = _local_store.db_path
        dash_port = _dashboard_mod.start_local_server(db_path=db_path, project=project)
        _config["dashboard_port"] = dash_port
        
        # Wire sleep trigger
        if _sleep_engine:
            _dashboard_mod.set_sleep_trigger(_sleep_engine.trigger_sleep)

        if first_run:
            _print_banner(project, embed_model, sleep_interval, sleep_on_exit, dash_port)
        # subsequent runs: silent

    elif mode == "self-host":
        # Remote client path — delegates to HTTP API
        try:
            from .client import NeuroSleepClient
            _config["_client"] = NeuroSleepClient(
                base_url=_config["host"],
                api_key=api_key or "",
            )
        except Exception as e:
            raise NSNConnectionError(f"Could not connect to self-host at {_config['host']}: {e}")
    else:
        raise ValueError(f"[NeuroSleepNet] Unknown mode '{mode}'. Use 'local' or 'self-host'.")

    _initialized = True


def _print_banner(project: str, embed_model: str, sleep_interval: int, sleep_on_exit: bool, dash_port: int = 3000):
    pid = project[:8] if len(project) >= 8 else project
    print()
    print(f"[NeuroSleepNet] Initializing project: {project}")
    print(f"[NeuroSleepNet] Mode: local (SQLite, in-process)")
    print(f"[NeuroSleepNet] Sleep Engine: active (cycle: {sleep_interval}s, sleep_on_exit: {'enabled' if sleep_on_exit else 'disabled'})")
    print(f"[NeuroSleepNet] Embed model: {embed_model}")
    print(f"[NeuroSleepNet] {'─' * 45}")
    print(f"[NeuroSleepNet] Dashboard live → http://localhost:{dash_port}/p/{pid}")
    print(f"[NeuroSleepNet] {'─' * 45}")
    print(f"[NeuroSleepNet] Ready. 0 memories | 0 users | 0 sleep cycles")
    print()


def _check_init():
    if not _initialized:
        raise NSNInitError("nsn.init() must be called before using NeuroSleepNet.")


def _get_embedding(text: str) -> List[float]:
    if _embed:
        try:
            return _embed.embed_single(text)
        except Exception:
            pass
    return []


# ── remember() ────────────────────────────────────────────────────────────────

def remember(
    content: str,
    user_id: Optional[str] = None,
    type: str = "episodic",
    importance: float = 1.0,
    tags: Optional[List[str]] = None,
    ttl_days: Optional[int] = None,
) -> Optional[Dict]:
    """Store a memory. Returns {id, status}."""
    _check_init()
    if _config["mode"] == "local":
        try:
            emb = _get_embedding(content)
            mid = _local_store.store(
                content=content,
                project=_config["project"],
                user_id=user_id,
                session_id=_config["session_id"],
                tags=tags or [],
                importance=importance,
                memory_type=type,
                embedding=emb if emb else None,
                ttl_days=ttl_days,
            )
            result = {"id": mid, "status": "stored"}
            _dashboard_mod.push_event("remember", {
                "id": mid, "content": content[:120], "type": type,
                "user_id": user_id, "importance": importance,
            })
            return result
        except Exception as e:
            _logger.warning(f"[NeuroSleepNet] remember() failed: {e}")
            return None
    else:
        return _remote_call("store_memory", content=content, user_id=user_id,
                            project=_config["project"],
                            memory_type=type, importance=importance)


# ── recall() ──────────────────────────────────────────────────────────────────

def recall(
    query: str,
    user_id: Optional[str] = None,
    top_k: int = 5,
    memory_types: Optional[List[str]] = None,
    min_score: Optional[float] = None,
) -> List[Dict]:
    """
    Retrieve memories relevant to query.
    Memories below recall_threshold are withheld and logged as misses.
    Returns List[Memory] with .content, .score, .id, .type, .pinned
    """
    _check_init()
    global _last_recalled

    threshold = min_score if min_score is not None else _config.get("recall_threshold", 0.6)

    if _config["mode"] == "local":
        try:
            emb = _get_embedding(query)
            if emb:
                candidates = _local_store.retrieve(
                    query=query,
                    query_embedding=emb,
                    project=_config["project"],
                    user_id=user_id,
                    top_k=top_k * 3,
                    memory_types=memory_types,
                    min_score=0.0,
                )
            elif _embed and _embed.is_tfidf():
                # TF-IDF fallback path — populate index from store, query via cosine
                all_mems = _local_store.list_memories(_config["project"], user_id=user_id, limit=2000)
                tfidf = _embed.tfidf_index()
                known = set(tfidf._ids)
                for m in all_mems:
                    if m["id"] not in known:
                        tfidf.add(m["id"], m.get("content", ""))
                candidates = _local_store.retrieve(
                    query=query,
                    query_embedding=None,
                    project=_config["project"],
                    user_id=user_id,
                    top_k=top_k * 3,
                    memory_types=memory_types,
                    min_score=0.0,
                    tfidf_index=tfidf,
                )
            else:
                candidates = _local_store.search_text(
                    query=query, project=_config["project"],
                    user_id=user_id, top_k=top_k,
                )
        except Exception as e:
            _logger.warning(f"[NeuroSleepNet] recall() failed: {e}")
            _last_recalled = []
            return []

        # Gate: split into hits and misses
        hits = []
        for mem in candidates:
            score = mem.get("attention_score", 0.0)
            if mem.get("pinned"):
                hits.append(mem)  # pins always pass
            elif score >= threshold:
                hits.append(mem)
            else:
                # Log as miss
                try:
                    _local_store.log_miss(
                        project=_config["project"],
                        query=query,
                        score=score,
                        threshold=threshold,
                        memory_id=mem.get("id"),
                        memory_content=mem.get("content", "")[:200],
                        user_id=user_id,
                        reason="below_threshold",
                    )
                except Exception:
                    pass

        _last_recalled = hits[:top_k]
        _dashboard_mod.push_event("recall", {
            "query": query[:100],
            "hits": len(_last_recalled),
            "misses": len(candidates) - len(hits),
            "user_id": user_id,
            "top_score": _last_recalled[0].get("attention_score", 0.0) if _last_recalled else 0.0,
        })
        return _last_recalled
    else:
        # Fix 11: pass min_score to the API so server applies gating where possible
        result = _remote_call(
            "retrieve",
            query=query,
            user_id=user_id,
            project=_config["project"],
            top_k=top_k * 3,  # fetch more so client-side gate can also filter
            memory_types=memory_types,
        )
        # Flatten the {"memory": ..., "attention_score": ...} structure to match local mode
        flattened = []
        for item in (result or []):
            m = item.get("memory", item)  # some server versions return flat dicts
            if "attention_score" not in m and "attention_score" in item:
                m["attention_score"] = item["attention_score"]
            if "why_retrieved" not in m and "why_retrieved" in item:
                m["why_retrieved"] = item["why_retrieved"]
            flattened.append(m)

        # Fix 11: apply client-side threshold gating — same logic as local path
        hits_sh = []
        for mem in flattened:
            score = mem.get("attention_score", 0.0) or 0.0
            if mem.get("pinned"):
                hits_sh.append(mem)
            elif score >= threshold:
                hits_sh.append(mem)
            else:
                # Log the miss to the dashboard event stream
                _dashboard_mod.push_event("miss", {
                    "query": query[:100],
                    "score": score,
                    "threshold": threshold,
                    "memory_id": mem.get("id", ""),
                    "user_id": user_id,
                    "reason": "below_threshold",
                })

        _last_recalled = hits_sh[:top_k]
        _dashboard_mod.push_event("recall", {
            "query": query[:100],
            "hits": len(_last_recalled),
            "misses": len(flattened) - len(hits_sh),
            "user_id": user_id,
            "top_score": _last_recalled[0].get("attention_score", 0.0) if _last_recalled else 0.0,
        })
        return _last_recalled


# ── forget() ──────────────────────────────────────────────────────────────────

def forget(memory_id: str) -> Dict:
    """Forget a specific memory by ID."""
    _check_init()
    if _config["mode"] == "local":
        ok = _local_store.forget_by_id(memory_id, _config["project"])
        return {"deleted": ok, "id": memory_id}
    return _remote_call("forget_by_id", memory_id=memory_id)


def forget_user(user_id: str) -> Dict:
    """Hard-delete all memories for a user (GDPR right-to-erasure)."""
    _check_init()
    if _config["mode"] == "local":
        count = _local_store.forget_user(user_id, _config["project"])
        return {"deleted": count, "user_id": user_id}
    return _remote_call("forget_user", user_id=user_id)


def forget_project(project: Optional[str] = None) -> Dict:
    """Delete all memories for a project."""
    _check_init()
    proj = project or _config["project"]
    if _config["mode"] == "local":
        count = _local_store.forget_project(proj)
        return {"deleted": count, "project": proj}
    return _remote_call("forget_project", project=proj)


# ── pin() ─────────────────────────────────────────────────────────────────────

def pin(
    content: str,
    user_id: Optional[str] = None,
    label: Optional[str] = None,
) -> Dict:
    """
    Pin a memory — permanent, immutable, always injected first.
    Pinned memories survive sleep cycles, decay, and dedup.
    user_id=None means the pin applies to all users in this project.
    """
    _check_init()
    if _config["mode"] == "local":
        emb = _get_embedding(content)
        mid = _local_store.pin_memory(
            content=content,
            project=_config["project"],
            user_id=user_id,
            label=label,
            embedding=emb if emb else None,
        )
        result = {"id": mid, "status": "pinned", "label": label}
        _dashboard_mod.push_event("pin", {
            "id": mid, "content": content[:120], "label": label, "user_id": user_id,
        })
        return result
    return _remote_call("pin", content=content, user_id=user_id, label=label)


def unpin(memory_id: str, confirm: bool = False) -> Dict:
    """Remove a pin. Requires confirm=True — pins are hard to delete by design."""
    _check_init()
    if not confirm:
        raise ValueError("unpin() requires confirm=True. Pins are permanent by design — pass confirm=True to proceed.")
    if _config["mode"] == "local":
        ok = _local_store.unpin_memory(memory_id, _config["project"])
        return {"unpinned": ok, "id": memory_id}
    return _remote_call("unpin", memory_id=memory_id)


def list_pins(user_id: Optional[str] = None) -> List[Dict]:
    """List all pinned memories for the current project."""
    _check_init()
    if _config["mode"] == "local":
        return _local_store.list_pins(_config["project"], user_id=user_id)
    return _remote_call("list_pins", user_id=user_id)


# ── feedback() ────────────────────────────────────────────────────────────────

def feedback(
    memory_id: str,
    helpful: bool,
    context: Optional[str] = None,
) -> Dict:
    """Explicit feedback — reinforce (helpful=True) or downweight (helpful=False) a recalled memory."""
    _check_init()
    if _config["mode"] == "local":
        ok = _local_store.update_feedback(memory_id=memory_id, project=_config["project"], helpful=helpful)
        return {"updated": ok, "memory_id": memory_id, "helpful": helpful}
    return _remote_call("feedback", memory_id=memory_id, helpful=helpful)


def feedback_batch(items: List[Dict]) -> Dict:
    """
    Bulk feedback. Each item: {"memory_id": "...", "helpful": True/False}
    """
    _check_init()
    updated = 0
    for item in items:
        try:
            r = feedback(memory_id=item["memory_id"], helpful=item["helpful"])
            if r.get("updated"):
                updated += 1
        except Exception as e:
            _logger.debug(f"[NeuroSleepNet] feedback_batch skip: {e}")
    return {"updated": updated, "total": len(items)}


# ── sleep control ─────────────────────────────────────────────────────────────

def sleep(project: Optional[str] = None) -> Dict:
    """Manually trigger a sleep cycle (consolidation + dedup + promotion)."""
    _check_init()
    if _config["mode"] == "local":
        return _sleep_engine.run_now()
    return _remote_call("trigger_sleep", project=project or _config["project"])


def sleep_status() -> Dict:
    """Get sleep engine status: last_sleep, next_sleep, cycles run, paused."""
    _check_init()
    if _config["mode"] == "local":
        return _sleep_engine.get_status()
    return _remote_call("sleep_status")


def sleep_pause() -> Dict:
    """Pause automatic sleep cycles."""
    _check_init()
    if _config["mode"] == "local":
        _sleep_engine.pause()
        return {"paused": True}
    return _remote_call("sleep_pause")


def sleep_resume() -> Dict:
    """Resume automatic sleep cycles."""
    _check_init()
    if _config["mode"] == "local":
        _sleep_engine.resume()
        return {"paused": False}
    return _remote_call("sleep_resume")


# ── inspection ────────────────────────────────────────────────────────────────

def list_memories(user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """List all memories for a user (or whole project if user_id=None)."""
    _check_init()
    if _config["mode"] == "local":
        return _local_store.list_memories(_config["project"], user_id=user_id, limit=limit)
    return _remote_call("list_memories", user_id=user_id, limit=limit)


def search(query: str, user_id: Optional[str] = None) -> List[Dict]:
    """Full-text search memories by content string."""
    _check_init()
    if _config["mode"] == "local":
        return _local_store.search_text(query, _config["project"], user_id=user_id)
    return _remote_call("search", query=query, user_id=user_id)


def stats() -> Dict:
    """Return memory statistics for the current project."""
    _check_init()
    if _config["mode"] == "local":
        s = _local_store.get_stats(_config["project"])
        s["sleep"] = _sleep_engine.get_status() if _sleep_engine else {}
        return s
    return _remote_call("stats")


def export(path: str) -> Dict:
    """Export all memories to a JSON file for backup/portability."""
    _check_init()
    if _config["mode"] == "local":
        items = _local_store.export_all(_config["project"])
        payload = {
            "project": _config["project"],
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "memories": items,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        return {"exported": len(items), "path": path}
    return _remote_call("export", path=path)


def import_memories(path: str) -> Dict:
    """Import memories from a JSON backup file."""
    _check_init()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("memories", raw) if isinstance(raw, dict) else raw
    if _config["mode"] == "local":
        count = _local_store.import_all(_config["project"], items)
        return {"imported": count, "total": len(items)}
    return _remote_call("import_memories", items=items)


def merge_projects(source_project: str, target_project: Optional[str] = None) -> Dict:
    """
    Merge all active memories from a source project into a target project.
    If target_project is None, merges into the current active project.
    """
    _check_init()
    target = target_project or _config["project"]
    if _config["mode"] == "local":
        items = _local_store.export_all(source_project)
        if not items:
            return {"merged": 0, "source": source_project, "target": target, "status": "no_memories_found"}
        
        count = _local_store.import_all(target, items)
        return {"merged": count, "source": source_project, "target": target}
    return _remote_call("merge_projects", source_project=source_project, target_project=target)


def dashboard(open_browser: bool = True):
    """Open the NeuroSleepNet dashboard in your browser."""
    _check_init()
    proj = _config.get("project", "default")
    if _config["mode"] == "local":
        port = _config.get("dashboard_port", 3000)
        url = f"http://localhost:{port}/p/{proj[:8]}"
        _dashboard_mod.open_dashboard(proj, port, open_browser=open_browser)
    else:
        url = f"{_config.get('host', 'http://localhost:8000').replace(':8000', ':3000')}/p/{proj[:8]}"
        print(f"[NeuroSleepNet] Opening dashboard → {url}")
        if open_browser:
            webbrowser.open(url)


# ── context() ─────────────────────────────────────────────────────────────────

def context(
    query: str,
    user_id: Optional[str] = None,
    max_tokens: int = 512,
    model_family: Optional[str] = None,   # Fix 3: None = use init() config default
    format: str = "auto",
    include_pins: bool = True,
    min_score: Optional[float] = None,
) -> str:
    """
    Build a memory context string ready to inject into a prompt.
    Positions and formats memory per model family's attention patterns.

    model_family: "phi3" | "mistral" | "gemma" | "llama3" | "generic"
                  None   = use the model_family set in nsn.init() (default: "generic")
    format:       "xml"  | "markdown" | "plain" | "auto"
    """
    _check_init()
    _family = model_family or _config.get("model_family", "generic")
    threshold = min_score if min_score is not None else _config.get("recall_threshold", 0.6)
    memories = recall(query=query, user_id=user_id, top_k=20, min_score=threshold)
    return build_context(
        memories=memories,
        query=query,
        max_tokens=max_tokens,
        model_family=_family,
        fmt=format,
        include_pins=include_pins,
    )


# ── wrap() ────────────────────────────────────────────────────────────────────

def wrap(
    fn: Callable,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    memory_types: Optional[List[str]] = None,
    streaming: bool = False,
) -> Callable:
    """
    Wrap any callable SLM/LLM with NeuroSleepNet memory.

    Hooks on structured I/O at the boundary. Does NOT monkey-patch internals.
    Streaming, tool calls, system prompts all pass through untouched.

    fn: Any function fn(prompt: str) -> str  OR  fn(messages: list) -> str
    """
    _check_init()

    model_name = getattr(fn, "model", getattr(fn, "model_name", "unknown"))
    strength = classify_model_strength(model_name)
    recommended = get_recommended_settings(strength)
    model_limit = get_model_context_limit(model_name)

    # Fix 3: detect model family from function/model name, fall back to init() config
    _wrap_family = (
        _detect_model_family(model_name)
        or _config.get("model_family", "generic")
    )

    top_k = recommended["top_k"]
    threshold = _config.get("recall_threshold", 0.6)
    implicit = _config.get("implicit_feedback", True)

    def _extract_query(args, kwargs) -> str:
        """Pull the user query string from positional or keyword args."""
        # fn(messages=[...]) — chat format
        messages = kwargs.get("messages") or (args[0] if args and isinstance(args[0], list) else None)
        if messages and isinstance(messages, list):
            user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
            return user_msgs[-1] if user_msgs else ""
        # fn(prompt: str) — simple format
        prompt = kwargs.get("prompt") or (args[0] if args and isinstance(args[0], str) else "")
        return prompt

    def _inject_context(query: str, args, kwargs, active_user_id: Optional[str] = None) -> tuple:
        """Retrieve memories and inject into prompt/messages."""
        global _last_recalled
        
        _uid = active_user_id or user_id

        # --- Implicit Feedback Loop (New Turn) ---
        if implicit and _last_recalled:
            # We have memories from the PREVIOUS turn. 
            # The current 'query' is the user's reaction to the agent's last answer.
            # Send it to the backend as implicit feedback signal.
            recall_ids = [str(m.get('id')) for m in _last_recalled if m.get('id')]
            
            # Fire-and-forget in a background thread to avoid blocking
            import threading
            def _send_feedback():
                try:
                    _remote_call(
                        "POST", "/api/v1/feedback/implicit",
                        json={"text": query, "memory_ids": recall_ids}
                    )
                except:
                    pass # SDK never crashes on background telemetry
            
            threading.Thread(target=_send_feedback, daemon=True).start()

        # --- Current Recall ---
        memories = recall(query=query, user_id=_uid, top_k=top_k,
                          memory_types=memory_types, min_score=threshold)
        _last_recalled = memories

        if not memories:
            return args, kwargs

        ctx_str = build_context(
            memories=memories,
            query=query,
            max_tokens=min(512, _config.get("memory_window", 4096) // 2),
            model_family=_wrap_family,   # Fix 3: use detected family, not hardcoded "generic"
        )
        if not ctx_str:
            return args, kwargs

        # Inject into messages or prompt
        messages = kwargs.get("messages") or (args[0] if args and isinstance(args[0], list) else None)
        if messages and isinstance(messages, list):
            new_messages = list(messages)
            # Inject as system message at start if none exists, else prepend to first system
            sys_idx = next((i for i, m in enumerate(new_messages) if m.get("role") == "system"), None)
            if sys_idx is not None:
                new_messages[sys_idx] = {
                    **new_messages[sys_idx],
                    "content": ctx_str + "\n\n" + new_messages[sys_idx]["content"],
                }
            else:
                new_messages.insert(0, {"role": "system", "content": ctx_str})
            if "messages" in kwargs:
                return args, {**kwargs, "messages": new_messages}
            new_args = (new_messages,) + args[1:]
            return new_args, kwargs
        else:
            prompt = kwargs.get("prompt") or (args[0] if args and isinstance(args[0], str) else "")
            augmented = ctx_str + "\n\n" + prompt
            if "prompt" in kwargs:
                return args, {**kwargs, "prompt": augmented}
            new_args = (augmented,) + (args[1:] if args else ())
            return new_args, kwargs

    def _store_interaction(query: str, response: str, active_user_id: Optional[str] = None):
        """Auto-log the interaction as an episodic memory."""
        if not query and not response:
            return
        _uid = active_user_id or user_id
        try:
            content = f"User: {query}\nAgent: {response}" if query else f"Agent: {response}"
            remember(content=content, user_id=_uid, type="episodic",
                     tags=["auto-wrap"])
        except Exception:
            pass

    if streaming:
        def streaming_wrapper(*args, **kwargs) -> Generator:
            query = _extract_query(args, kwargs)
            new_args, new_kwargs = _inject_context(query, args, kwargs)
            try:
                chunks = []
                for chunk in fn(*new_args, **new_kwargs):
                    chunks.append(chunk)
                    yield chunk
                response = "".join(str(c) for c in chunks)
                _store_interaction(query, response)
            except Exception as e:
                _logger.warning(f"[NeuroSleepNet] wrap() streaming error: {e}")
                # Fallback: call original unmodified
                yield from fn(*args, **kwargs)
        streaming_wrapper.__wrapped__ = fn  # type: ignore
        streaming_wrapper.__nsn__ = True    # type: ignore
        return streaming_wrapper

    _prev_query: Dict[str, Any] = {}  # closure state for implicit feedback

    def wrapped(*args, **kwargs) -> Any:
        active_user_id = kwargs.get("user_id") or user_id
        query = _extract_query(args, kwargs)

        # Implicit feedback: evaluate previous turn's follow-up
        if implicit and _prev_query.get("memories") and query:
            try:
                from .feedback import score_implicit
                signal = score_implicit(query)
                _logger.debug(f"[NeuroSleepNet] Implicit feedback signal check for '{query}': {signal}")
                if signal != 0.0:
                    helpful = signal > 0.0
                    for mem in _prev_query["memories"]:
                        if mem.get("id"):
                            _logger.debug(f"[NeuroSleepNet] Applying implicit feedback ({'helpful' if helpful else 'unhelpful'}) to {mem['id'][:8]}")
                            feedback(memory_id=mem["id"], helpful=helpful)
            except Exception as e:
                _logger.debug(f"[NeuroSleepNet] Implicit feedback failed: {e}")

        new_args, new_kwargs = _inject_context(query, args, kwargs, active_user_id)

        try:
            response = fn(*new_args, **new_kwargs)
        except Exception as e:
            _logger.warning(f"[NeuroSleepNet] wrap() failed to call fn: {e}. Falling back to original.")
            response = fn(*args, **kwargs)

        resp_str = str(response) if not isinstance(response, str) else response
        _store_interaction(query, resp_str, active_user_id)

        _prev_query["query"] = query
        _prev_query["memories"] = list(_last_recalled)

        return response

    wrapped.__wrapped__ = fn  # type: ignore
    wrapped.__nsn__ = True    # type: ignore
    return wrapped


# ── internal remote call helper ───────────────────────────────────────────────

def _remote_call(method: str, **kwargs) -> Any:
    client = _config.get("_client")
    if not client:
        raise NSNInitError("Not connected to a self-host instance. Call nsn.init(mode='self-host', host=...) first.")
    try:
        return getattr(client, method)(**kwargs)
    except Exception as e:
        raise NSNConnectionError(f"Remote call '{method}' failed: {e}") from e


def get_config():
    """Return the active configuration dictionary."""
    return _config


def get_embed():
    """Return the active EmbeddingManager (for testing and introspection)."""
    return _embed
