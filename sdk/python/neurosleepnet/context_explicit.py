"""
NSNContext — Explicit context manager for NeuroSleepNet (Phase 6.1).

Replaces the global singleton with a class that can be instantiated
multiple times for different projects or configurations.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import uuid as _uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .embeddings import EmbeddingManager
from .local_sleep import LocalSleepEngine
from .local_store import LocalStore
from .feedback import apply_implicit_feedback

logger = logging.getLogger("neurosleepnet")


@dataclasses.dataclass
class NSNContext:
    """
    Explicit NeuroSleepNet context that replaces the global singleton.
    
    Each instance manages its own resources: store, embeddings, sleep engine,
    and thread pool. Multiple contexts can coexist for different projects.
    """
    config: Dict[str, Any] = dataclasses.field(default_factory=dict)
    local_store: Optional[LocalStore] = None
    embed: Optional[EmbeddingManager] = None
    sleep_engine: Optional[LocalSleepEngine] = None
    last_recalled: List[Dict] = dataclasses.field(default_factory=list)
    initialized: bool = False
    session_id: str = dataclasses.field(default_factory=lambda: str(_uuid.uuid4()))
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    _executor: Optional[ThreadPoolExecutor] = None

    def __post_init__(self):
        """Initialize context with safe defaults."""
        if not self.config:
            self.config = {
                "project": "default",
                "mode": "local",
                "host": "http://localhost:8000/api",
                "memory_window": 4096,
                "sleep_interval": 300,
                "sleep_on_exit": True,
                "embed_model": "local",
                "recall_threshold": None,
                "implicit_feedback": True,
                "decay": True,
                "model_family": "generic",
                "debug": False,
                "data_dir": "~/.neurosleepnet",
                "embedding_model": None,
                "synthesis_mode": False,
            }

    def init(
        self,
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
    ) -> None:
        """Initialize this context with the given configuration."""
        with self.lock:
            # Shutdown existing resources if reinitializing
            if self.initialized:
                self.shutdown()

            # Update config
            self.config.update({
                "project": project,
                "mode": mode,
                "host": host or "http://localhost:8000/api",
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
                "session_id": self.session_id,
            })

            # Setup logging
            log_level = logging.DEBUG if debug else logging.WARNING
            logging.basicConfig(level=log_level)
            logger.setLevel(log_level)

            # Initialize components based on mode
            if mode == "local":
                self.local_store = LocalStore(data_dir=data_dir)
                self.embed = EmbeddingManager(
                    provider=embed_model,
                    model_name=embedding_model,
                    api_key=api_key,
                )
                self.sleep_engine = LocalSleepEngine(
                    store=self.local_store,
                    project=project,
                    interval_seconds=float(sleep_interval),
                    sleep_on_exit=sleep_on_exit,
                )
                self.sleep_engine.start()

                # Initialize thread pool for implicit feedback
                if self._executor:
                    self._executor.shutdown(wait=False)
                self._executor = ThreadPoolExecutor(
                    max_workers=4, thread_name_prefix="nsn-feedback"
                )

                # Trigger embedding load
                try:
                    self.embed._ensure_loaded()
                except Exception as e:
                    logger.warning(f"[NeuroSleepNet] Embedding engine warning: {e}")

            elif mode == "self-host":
                try:
                    from .client import NeuroSleepClient
                    self.config["_client"] = NeuroSleepClient(
                        base_url=self.config["host"],
                        api_key=api_key or "",
                    )
                except Exception as e:
                    raise RuntimeError(f"Could not connect to self-host at {self.config['host']}: {e}")
            else:
                raise ValueError(f"[NeuroSleepNet] Unknown mode '{mode}'. Use 'local' or 'self-host'.")

            self.initialized = True

    def shutdown(self) -> None:
        """Gracefully stop background resources."""
        with self.lock:
            if self._executor:
                self._executor.shutdown(wait=False)
                self._executor = None
            if self.sleep_engine:
                self.sleep_engine.stop()
            self.initialized = False

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using this context's embedding manager."""
        if self.embed:
            try:
                return self.embed.embed_single(text)
            except Exception:
                pass
        return []

    def remember(self, content: str, **kwargs) -> str:
        """Store a memory using this context."""
        if not self.initialized:
            raise RuntimeError("NSNContext not initialized. Call init() first.")
        
        if self.local_store:
            return self.local_store.store(content, project=self.config["project"], **kwargs)
        raise RuntimeError("Remember not available in current mode")

    def recall(self, query: str, **kwargs) -> List[Dict]:
        """Recall memories using this context."""
        if not self.initialized:
            raise RuntimeError("NSNContext not initialized. Call init() first.")
        
        if self.local_store:
            return self.local_store.retrieve(query, project=self.config["project"], **kwargs)
        raise RuntimeError("Recall not available in current mode")

    def apply_implicit_feedback(self, query: str) -> None:
        """Apply implicit feedback for the last recalled memories."""
        if (self.config.get("implicit_feedback") and 
            self.last_recalled and 
            query and 
            self.config["mode"] == "local" and 
            self.local_store and 
            self._executor):
            self._executor.submit(
                apply_implicit_feedback,
                self.local_store,
                self.config["project"],
                list(self.last_recalled),
                query,
            )


# Global context registry for backward compatibility
_contexts: Dict[str, NSNContext] = {}

def get_context(name: str = "default") -> NSNContext:
    """Get or create a named context."""
    if name not in _contexts:
        _contexts[name] = NSNContext()
    return _contexts[name]

def init_context(name: str = "default", **kwargs) -> NSNContext:
    """Initialize a named context with configuration."""
    if name not in _contexts:
        _contexts[name] = NSNContext()
    _contexts[name].init(**kwargs)
    return _contexts[name]

def shutdown_context(name: str = "default") -> None:
    """Shutdown a named context."""
    if name in _contexts:
        _contexts[name].shutdown()
        del _contexts[name]

# Export the new explicit context
__all__ = [
    "NSNContext",
    "get_context",
    "init_context", 
    "shutdown_context",
]
