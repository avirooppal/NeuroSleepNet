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
import dataclasses
import json
import logging
import os
import threading
import time
import uuid as _uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
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
    MODEL_FAMILY_TEMPLATES,
)
from .context_explicit import NSNContext, get_context, init_context, shutdown_context
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
    "NSNResult", "NSNRecallError",
    "NSNAuthError", "NSNConnectionError", "NSNInitError",
    "NSNContext", "get_context", "init_context", "shutdown_context",
]

# ── Exceptions ─────────────────────────────────────────────────────────────────

class NSNAuthError(RuntimeError): pass
class NSNConnectionError(RuntimeError): pass
class NSNInitError(RuntimeError): pass
class NSNRecallError(RuntimeError): pass


@dataclasses.dataclass
class NSNResult:
    """
    Fix 2.4: Lightweight result envelope for SDK operations.
    Replaces silent None/[] returns on failure with structured error info.
    """
    ok: bool
    value: Any = None
    error: str = ""
    error_code: str = ""  # e.g. "STORE_FAILED", "EMBED_FAILED", "RECALL_FAILED"

    def __bool__(self):
        return self.ok


# ── Context Management (Phase 6.1) ─────────────────────────────────────
# Use explicit context instead of global singleton

def _get_default_context() -> NSNContext:
    """Get the default named context for backward compatibility."""
    return get_context("default")


# ── init() ─────────────────────────────────────────────────────────────────────

def init(
    project: str = "default",
    mode: str = "local",
    host: Optional[str] = None,
    api_key: Optional[str] = None,
    memory_window: int = 4096,
    sleep_interval: int = 300,
    sleep_on_exit: bool = True,
    embed_model: str = "local",
    recall_threshold: Optional[float] = None,
    implicit_feedback: bool = True,
    decay: bool = True,
    model_family: str = "generic",
    debug: bool = False,
    data_dir: Optional[str] = None,
    embedding_model: Optional[str] = None,
    synthesis_mode: bool = False,
):
    """Initialize NeuroSleepNet. Call once at startup."""
    # Phase 6.1: Use explicit context instead of global singleton
    ctx = _get_default_context()
    
    with ctx.lock:
        # Fix 2.3: Shut down existing background resources before reinitializing
        if ctx.initialized:
            ctx.shutdown()

        log_level = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(level=log_level)
        logger.setLevel(log_level)

        # Adaptive Default: Colab-aware data_dir
        if not data_dir:
            is_colab = False
            try:
                import google.colab
                is_colab = True
            except ImportError: pass
            
            if is_colab and os.path.exists("/content/drive/MyDrive"):
                data_dir = "/content/drive/MyDrive/neurosleepnet"
            else:
                data_dir = "~/.neurosleepnet"

        ctx.config.update({
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
            "model_family": model_family,
            "debug": debug,
            "data_dir": data_dir,
            "embedding_model": embedding_model,
            "synthesis_mode": synthesis_mode,
            "session_id": ctx.session_id,
        })

        if mode == "local":
            ctx.local_store = LocalStore(data_dir=data_dir)
            ctx.embed = EmbeddingManager(
                provider=embed_model,
                model_name=embedding_model,
                api_key=api_key,
            )
            ctx.sleep_engine = LocalSleepEngine(
                store=ctx.local_store,
                project=project,
                interval_seconds=float(sleep_interval),
                sleep_on_exit=sleep_on_exit,
            )
            ctx.sleep_engine.start()

            # Fix 2.2: Bounded thread pool for implicit feedback
            if ctx._executor:
                ctx._executor.shutdown(wait=False)
            ctx._executor = ThreadPoolExecutor(
                max_workers=4, thread_name_prefix="nsn-feedback"
            )
            
            # Fix 5: Proactively trigger embedding load to detect issues at init time
            try:
                ctx.embed._ensure_loaded()
            except Exception as e:
                logger.warning(f"[NeuroSleepNet] Embedding engine warning: {e}")

            first_run = ctx.local_store._is_first_run(project)
            ctx.local_store.mark_seen(project)

            # Start local dashboard server
            db_path = ctx.local_store.db_path
            dash_port = _dashboard_mod.start_local_server(db_path=db_path, project=project)
            ctx.config["dashboard_port"] = dash_port
            
            # Wire sleep trigger
            if ctx.sleep_engine:
                _dashboard_mod.set_sleep_trigger(ctx.sleep_engine.trigger_sleep)

            # Sync with CLI config for easy 'nsn dashboard' usage
            try:
                with open(".nsn.json", "w") as f:
                    json.dump({"project_id": project, "data_dir": data_dir}, f, indent=2)
            except Exception:
                pass

            if first_run:
                _print_banner(project, embed_model, sleep_interval, sleep_on_exit, dash_port)

        elif mode == "self-host":
            try:
                from .client import NeuroSleepClient
                ctx.config["_client"] = NeuroSleepClient(
                    base_url=ctx.config["host"],
                    api_key=api_key or "",
                )
            except Exception as e:
                raise NSNConnectionError(f"Could not connect to self-host at {ctx.config['host']}: {e}")
        else:
            raise ValueError(f"[NeuroSleepNet] Unknown mode '{mode}'. Use 'local' or 'self-host'.")

        ctx.initialized = True


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
    ctx = _get_default_context()
    if not ctx.initialized:
        raise NSNInitError("nsn.init() must be called before using NeuroSleepNet.")


def _get_embedding(text: str) -> List[float]:
    ctx = _get_default_context()
    if ctx.embed:
        try:
            return ctx.embed.embed_single(text)
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
) -> NSNResult:
    """Store a memory. Returns NSNResult with memory dict on success."""
    ctx = _get_default_context()
    _check_init()
    if ctx.config["mode"] == "local":
        try:
            emb = _get_embedding(content)
            if not emb:
                return NSNResult(
                    ok=False,
                    error="Embedding generation failed; cannot store memory.",
                    error_code="EMBED_FAILED"
                )
            mid = ctx.local_store.store(
                content=content,
                project=ctx.config["project"],
                user_id=user_id,
                session_id=ctx.config["session_id"],
                tags=tags or [],
                importance=importance,
                memory_type=type,
                embedding=emb,
                ttl_days=ttl_days,
            )
            result = {"id": mid, "status": "stored"}
            _dashboard_mod.push_event("remember", {
                "id": mid, "content": content[:120], "type": type,
                "user_id": user_id, "importance": importance,
            })
            return NSNResult(ok=True, value=result)
        except Exception as e:
            logger.warning(f"[NeuroSleepNet] remember() failed: {e}")
            return NSNResult(
                ok=False,
                error=str(e),
                error_code="STORE_FAILED"
            )
    else:
        # Fix 2.4: Propagate remote errors instead of swallowing
        try:
            remote_val = _remote_call("store_memory", content=content, user_id=user_id,
                                   project=ctx.config["project"],
                                   memory_type=type, importance=importance)
            return NSNResult(ok=True, value=remote_val)
        except Exception as e:
            return NSNResult(
                ok=False,
                error=str(e),
                error_code="REMOTE_STORE_FAILED"
            )


# ── recall() ──────────────────────────────────────────────────────────────────

def recall(
    query: str,
    user_id: Optional[str] = None,
    top_k: int = 5,
    memory_types: Optional[List[str]] = None,
    min_score: Optional[float] = None,
) -> NSNResult:
    """
    Retrieve memories relevant to query.
    Returns NSNResult with list of memory dicts on success.
    """
    _check_init()

    threshold = min_score if min_score is not None else (_ctx.config.get("recall_threshold") or 0.6)

    if _ctx.config["mode"] == "local":
        try:
            emb = _get_embedding(query)
            if emb:
                candidates = _ctx.local_store.retrieve(
                    query=query,
                    query_embedding=emb,
                    project=_ctx.config["project"],
                    user_id=user_id,
                    top_k=top_k * 3,
                    memory_types=memory_types,
                    min_score=0.0,
                )
            elif _ctx.embed and _ctx.embed.is_tfidf():
                # TF-IDF fallback path — populate index from store, query via cosine
                all_mems = _ctx.local_store.list_memories(_ctx.config["project"], user_id=user_id, limit=2000)
                tfidf = _ctx.embed.tfidf_index()
                known = set(tfidf._ids)
                for m in all_mems:
                    if m["id"] not in known:
                        tfidf.add(m["id"], m.get("content", ""))
                candidates = _ctx.local_store.retrieve(
                    query=query,
                    query_embedding=None,
                    project=_ctx.config["project"],
                    user_id=user_id,
                    top_k=top_k * 3,
                    memory_types=memory_types,
                    min_score=0.0,
                    tfidf_index=tfidf,
                )
            else:
                candidates = _ctx.local_store.search_text(
                    query=query, project=_ctx.config["project"],
                    user_id=user_id, top_k=top_k,
                )
        except Exception as e:
            _logger.error(f"[NeuroSleepNet] recall() failed: {e}")
            raise NSNRecallError(f"Recall failed: {e}") from e

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
                    _ctx.local_store.log_miss(
                        project=_ctx.config["project"],
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

        _ctx.last_recalled = hits[:top_k]
        _dashboard_mod.push_event("recall", {
            "query": query[:100],
            "hits": len(_ctx.last_recalled),
            "misses": len(candidates) - len(hits),
            "user_id": user_id,
            "top_score": _ctx.last_recalled[0].get("attention_score", 0.0) if _ctx.last_recalled else 0.0,
        })
        return NSNResult(ok=True, value=_ctx.last_recalled)
    else:
        # Fix 11: pass min_score to the API so server applies gating where possible
        try:
            result = _remote_call(
                "retrieve",
                query=query,
                user_id=user_id,
                project=_ctx.config["project"],
                top_k=top_k * 3,  # fetch more so client-side gate can also filter
                memory_types=memory_types,
            )
        except Exception as e:
            return NSNResult(
                ok=False,
                error=str(e),
                error_code="REMOTE_RECALL_FAILED"
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

        _ctx.last_recalled = hits_sh[:top_k]
        _dashboard_mod.push_event("recall", {
            "query": query[:100],
            "hits": len(_ctx.last_recalled),
            "misses": len(flattened) - len(hits_sh),
            "user_id": user_id,
            "top_score": _ctx.last_recalled[0].get("attention_score", 0.0) if _ctx.last_recalled else 0.0,
        })
        return NSNResult(ok=True, value=_ctx.last_recalled)


# ── forget() ──────────────────────────────────────────────────────────────────

def forget(memory_id: str) -> Dict:
    """Forget a specific memory by ID."""
    _check_init()
    if _ctx.config["mode"] == "local":
        ok = _ctx.local_store.forget_by_id(memory_id, _ctx.config["project"])
        return {"deleted": ok, "id": memory_id}
    return _remote_call("forget_by_id", memory_id=memory_id)


def forget_user(user_id: str) -> Dict:
    """Hard-delete all memories for a user (GDPR right-to-erasure)."""
    _check_init()
    if _ctx.config["mode"] == "local":
        count = _ctx.local_store.forget_user(user_id, _ctx.config["project"])
        return {"deleted": count, "user_id": user_id}
    return _remote_call("forget_user", user_id=user_id)


def forget_project(project: Optional[str] = None) -> Dict:
    """Delete all memories for a project."""
    _check_init()
    proj = project or _ctx.config["project"]
    if _ctx.config["mode"] == "local":
        count = _ctx.local_store.forget_project(proj)
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
    if _ctx.config["mode"] == "local":
        emb = _get_embedding(content)
        mid = _ctx.local_store.pin_memory(
            content=content,
            project=_ctx.config["project"],
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
    if _ctx.config["mode"] == "local":
        ok = _ctx.local_store.unpin_memory(memory_id, _ctx.config["project"])
        return {"unpinned": ok, "id": memory_id}
    return _remote_call("unpin", memory_id=memory_id)


def list_pins(user_id: Optional[str] = None) -> List[Dict]:
    """List all pinned memories for the current project."""
    _check_init()
    if _ctx.config["mode"] == "local":
        return _ctx.local_store.list_pins(_ctx.config["project"], user_id=user_id)
    return _remote_call("list_pins", user_id=user_id)


# ── feedback() ────────────────────────────────────────────────────────────────

def feedback(
    memory_id: str,
    helpful: bool,
    context: Optional[str] = None,
) -> Dict:
    """Explicit feedback — reinforce (helpful=True) or downweight (helpful=False) a recalled memory."""
    _check_init()
    if _ctx.config["mode"] == "local":
        ok = _ctx.local_store.update_feedback(memory_id=memory_id, project=_ctx.config["project"], helpful=helpful)
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
    if _ctx.config["mode"] == "local":
        return _ctx.sleep_engine.run_now()
    return _remote_call("trigger_sleep", project=project or _ctx.config["project"])


def sleep_status() -> Dict:
    """Get sleep engine status: last_sleep, next_sleep, cycles run, paused."""
    _check_init()
    if _ctx.config["mode"] == "local":
        return _ctx.sleep_engine.get_status()
    return _remote_call("sleep_status")


def sleep_pause() -> Dict:
    """Pause automatic sleep cycles."""
    _check_init()
    if _ctx.config["mode"] == "local":
        _ctx.sleep_engine.pause()
        return {"paused": True}
    return _remote_call("sleep_pause")


def sleep_resume() -> Dict:
    """Resume automatic sleep cycles."""
    _check_init()
    if _ctx.config["mode"] == "local":
        _ctx.sleep_engine.resume()
        return {"paused": False}
    return _remote_call("sleep_resume")


# ── inspection ────────────────────────────────────────────────────────────────

def list_memories(user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """List all memories for a user (or whole project if user_id=None)."""
    _check_init()
    if _ctx.config["mode"] == "local":
        return _ctx.local_store.list_memories(_ctx.config["project"], user_id=user_id, limit=limit)
    return _remote_call("list_memories", user_id=user_id, limit=limit)


def search(query: str, user_id: Optional[str] = None) -> List[Dict]:
    """Full-text search memories by content string."""
    _check_init()
    if _ctx.config["mode"] == "local":
        return _ctx.local_store.search_text(query, _ctx.config["project"], user_id=user_id)
    return _remote_call("search", query=query, user_id=user_id)


def stats() -> Dict:
    """Return memory statistics for the current project."""
    _check_init()
    if _ctx.config["mode"] == "local":
        s = _ctx.local_store.get_stats(_ctx.config["project"])
        s["sleep"] = _ctx.sleep_engine.get_status() if _ctx.sleep_engine else {}
        return s
    return _remote_call("stats")


def export(path: str) -> Dict:
    """Export all memories to a JSON file for backup/portability."""
    _check_init()
    if _ctx.config["mode"] == "local":
        items = _ctx.local_store.export_all(_ctx.config["project"])
        payload = {
            "project": _ctx.config["project"],
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
    if _ctx.config["mode"] == "local":
        count = _ctx.local_store.import_all(_ctx.config["project"], items)
        return {"imported": count, "total": len(items)}
    return _remote_call("import_memories", items=items)


def merge_projects(source_project: str, target_project: Optional[str] = None) -> Dict:
    """
    Merge all active memories from a source project into a target project.
    If target_project is None, merges into the current active project.
    """
    _check_init()
    target = target_project or _ctx.config["project"]
    if _ctx.config["mode"] == "local":
        items = _ctx.local_store.export_all(source_project)
        if not items:
            return {"merged": 0, "source": source_project, "target": target, "status": "no_memories_found"}
        
        count = _ctx.local_store.import_all(target, items)
        return {"merged": count, "source": source_project, "target": target}
    return _remote_call("merge_projects", source_project=source_project, target_project=target)


def dashboard(open_browser: bool = True):
    """Open the NeuroSleepNet dashboard in your browser."""
    _check_init()
    proj = _ctx.config.get("project", "default")
    if _ctx.config["mode"] == "local":
        port = _ctx.config.get("dashboard_port", 3000)
        url = f"http://localhost:{port}/p/{proj[:8]}"
        _dashboard_mod.open_dashboard(proj, port, open_browser=open_browser)
    else:
        url = f"{_ctx.config.get('host', 'http://localhost:8000').replace(':8000', ':3000')}/p/{proj[:8]}"
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
    _family = model_family or _ctx.config.get("model_family", "generic")
    threshold = min_score if min_score is not None else (_ctx.config.get("recall_threshold") or 0.6)
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
    # Zero-config: init() is now called automatically in wrapped() if needed.

    # Fix 11: Adaptive defaults for different model strengths
    model_name = getattr(fn, "__name__", "generic")
    strength = classify_model_strength(model_name)
    rec = get_recommended_settings(strength)
    
    # User config in init() takes precedence over adaptive defaults.
    threshold = _ctx.config.get("recall_threshold", rec["min_score"])
    top_k = rec["top_k"]  # Can be expanded in future to support wrap(top_k=...)
    implicit = _ctx.config.get("implicit_feedback", True)
    model_limit = get_model_context_limit(model_name)

    # Fix 3: detect model family from function/model name, fall back to init() config
    _wrap_family = (
        _detect_model_family(model_name)
        or _ctx.config.get("model_family", "generic")
    )

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
        
        _uid = active_user_id or user_id

        # --- Implicit Feedback Loop (P0-3 fix) ---
        # Apply feedback for the PREVIOUS turn's recalled memories.
        # Old code called a dead remote endpoint in local mode — fixed to
        # dispatch directly to apply_implicit_feedback() from feedback.py.
        if implicit and _ctx.last_recalled and query:
            if _ctx.config["mode"] == "local" and _ctx.local_store and _ctx._executor:
                from .feedback import apply_implicit_feedback as _apply_fb
                # Fix 2.2: Use bounded executor instead of spawning a thread per call
                _ctx._executor.submit(
                    _apply_fb,
                    _ctx.local_store,
                    _ctx.config["project"],
                    list(_ctx.last_recalled),
                    query,
                )

        # --- Current Recall ---
        memories = recall(query=query, user_id=_uid, top_k=top_k,
                          memory_types=memory_types, min_score=threshold)
        _ctx.last_recalled = memories

        if not memories:
            return args, kwargs

        # Fix 4: Token limit awareness. Estimate tokens in current query + prompt.
        current_tokens = estimate_tokens(query)
        # Add safety buffer
        available_budget = max(0, model_limit - current_tokens - 256)
        
        # Respect the user's config memory_window if it's smaller than the model's budget
        injection_budget = min(available_budget, _ctx.config.get("memory_window", 4096) // 2)

        ctx_str = build_context(
            memories=memories,
            query=query,
            max_tokens=injection_budget,
            model_family=_wrap_family,   # Fix 3: use detected family, not hardcoded "generic"
        )
        
        template = MODEL_FAMILY_TEMPLATES.get(_wrap_family, MODEL_FAMILY_TEMPLATES["generic"])
        
        if ctx_str:
            _logger.debug(f"[NeuroSleepNet] Injected context: {ctx_str[:100]}...")
            # print(f"\n[DEBUG] Injected Context:\n{ctx_str}\n")
        
        if not ctx_str:
            return args, kwargs

        # Inject into messages or prompt
        messages = kwargs.get("messages") or (args[0] if args and isinstance(args[0], list) else None)
        if messages and isinstance(messages, list):
            new_messages = list(messages)
            pos = template.get("position", "system")
            
            if pos == "system":
                # Inject as system message at start if none exists, else prepend to first system
                sys_idx = next((i for i, m in enumerate(new_messages) if m.get("role") == "system"), None)
                if sys_idx is not None:
                    new_messages[sys_idx] = {
                        **new_messages[sys_idx],
                        "content": ctx_str + "\n\n" + new_messages[sys_idx]["content"],
                    }
                else:
                    new_messages.insert(0, {"role": "system", "content": ctx_str})
            else:
                # 'top' or 'human' -> inject into the first user message
                user_idx = next((i for i, m in enumerate(new_messages) if m.get("role") == "user"), None)
                if user_idx is not None:
                    new_messages[user_idx] = {
                        **new_messages[user_idx],
                        "content": ctx_str + "\n\n" + new_messages[user_idx]["content"],
                    }
                else:
                    new_messages.insert(0, {"role": "user", "content": ctx_str})
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
        # Fix 12: Zero-config auto-init
        if not _ctx.initialized:
            _logger.info("[NeuroSleepNet] wrap() called before init(). Using smart defaults.")
            init(project="auto-agent")

        active_user_id = kwargs.pop("user_id", None) or user_id
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
        _prev_query["memories"] = list(_ctx.last_recalled)

        return response

    wrapped.__wrapped__ = fn  # type: ignore
    wrapped.__nsn__ = True    # type: ignore
    return wrapped


# ── internal remote call helper ───────────────────────────────────────────────

def _remote_call(method: str, **kwargs) -> Any:
    client = _ctx.config.get("_client")
    if not client:
        raise NSNInitError("Not connected to a self-host instance. Call nsn.init(mode='self-host', host=...) first.")
    try:
        return getattr(client, method)(**kwargs)
    except Exception as e:
        raise NSNConnectionError(f"Remote call '{method}' failed: {e}") from e


def get_config():
    """Return the active configuration dictionary."""
    return _ctx.config


def get_embed():
    """Return the active EmbeddingManager (for testing and introspection)."""
    return _ctx.embed
