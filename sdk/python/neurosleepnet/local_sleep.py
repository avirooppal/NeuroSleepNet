"""
LocalSleepEngine — in-process sleep consolidation for NeuroSleepNet Import Mode.

Features:
- Background daemon thread with configurable interval
- sleep_on_exit: atexit hook fires consolidation on clean process exit
- pause() / resume() support
- get_status() returns last_sleep, next_sleep, stats
- Delegates dedup + promotion to LocalStore.run_consolidation()
"""
import atexit
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("neurosleepnet.sleep")


# ── Jaccard-dedup sentence synthesizer (P1-2) ─────────────────────────────────

def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity on word sets."""
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _jaccard_synthesize(cluster: List[Dict], max_sentences: int = 3) -> str:
    """
    P1-2: Real fallback synthesis using Jaccard-dedup sentence concatenation.

    Algorithm:
    1. Split every memory into sentences (split on . ! ?).
    2. Sort sentences by length descending (longer = more informative).
    3. Greedily select sentences where Jaccard vs all already-selected < 0.5.
    4. Take up to max_sentences.
    5. Join with space.

    This produces a genuine multi-fact summary without requiring an LLM,
    replacing the old 'longest content wins' selection.
    """
    import re
    all_sentences: List[str] = []
    for m in cluster:
        raw = m.get("content", "").strip()
        parts = re.split(r'(?<=[.!?])\s+', raw)
        all_sentences.extend([s.strip() for s in parts if len(s.strip()) > 10])

    if not all_sentences:
        return cluster[0]["content"]

    # Longer sentences carry more information — prefer them
    candidates = sorted(all_sentences, key=len, reverse=True)
    selected: List[str] = []
    for candidate in candidates:
        if all(_jaccard(candidate, s) < 0.5 for s in selected):
            selected.append(candidate)
        if len(selected) >= max_sentences:
            break

    return " ".join(selected) if selected else cluster[0]["content"]


class Synthesizer(ABC):
    @abstractmethod
    def synthesize(self, memories: List[Dict]) -> str:
        """Synthesize multiple memories into a single semantic fact."""
        pass


class LocalSleepEngine:
    def __init__(self, store, project: Optional[str] = None,
                 interval_seconds: float = 300.0, sleep_on_exit: bool = True,
                 synthesizer: Optional[Synthesizer] = None):
        self.store = store
        self.project = project
        self.interval_seconds = interval_seconds
        self.synthesizer = synthesizer
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default
        self._last_run: Optional[float] = None
        self._last_stats: Dict[str, Any] = {}
        self._run_count = 0
        self._sleep_on_exit = sleep_on_exit
        self._atexit_registered = False

        if sleep_on_exit:
            self._atexit_ref = self._on_exit
            atexit.register(self._atexit_ref)
            self._atexit_registered = True

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="NSN-SleepThread"
        )
        self._thread.start()
        logger.debug(f"[NeuroSleepNet] Sleep engine started (interval={self.interval_seconds}s, sleep_on_exit={self._sleep_on_exit})")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        # Fix 2.3: Unregister atexit handler so it doesn't fire on next init()
        if self._atexit_registered and self._atexit_ref:
            atexit.unregister(self._atexit_ref)
            self._atexit_registered = False

    def pause(self):
        self._pause_event.clear()
        logger.info("[NeuroSleepNet] Sleep engine paused.")

    def resume(self):
        self._pause_event.set()
        logger.info("[NeuroSleepNet] Sleep engine resumed.")

    # ── manual trigger ─────────────────────────────────────────────────────────
    
    def trigger_sleep(self) -> Dict[str, Any]:
        """Manual trigger alias for dashboard/API."""
        return self.run_now()

    def run_now(self) -> Dict[str, Any]:
        logger.info("[NeuroSleepNet] Running sleep consolidation...")
        try:
            stats = self.store.run_consolidation(project=self.project)
            self._last_run = time.time()
            self._last_stats = stats
            self._run_count += 1
            logger.info(f"[NeuroSleepNet] Sleep complete: {stats}")
            return stats
        except Exception as e:
            logger.error(f"[NeuroSleepNet] Sleep failed: {e}")
            return {"error": str(e)}

    # ── status ─────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        paused = not self._pause_event.is_set()
        last_sleep = (
            datetime.fromtimestamp(self._last_run, tz=timezone.utc).isoformat()
            if self._last_run else None
        )
        next_sleep = (
            datetime.fromtimestamp(self._last_run + self.interval_seconds, tz=timezone.utc).isoformat()
            if self._last_run else "pending"
        )
        return {
            "last_sleep": last_sleep,
            "next_sleep": next_sleep,
            "sleep_cycles_run": self._run_count,
            "paused": paused,
            "thread_alive": bool(self._thread and self._thread.is_alive()),
            "sleep_on_exit": self._sleep_on_exit,
            **self._last_stats,
        }

    # ── internals ──────────────────────────────────────────────────────────────

    def _run_loop(self):
        # Brief initial delay before first auto-run
        initial = min(60.0, self.interval_seconds * 0.1)
        deadline = time.monotonic() + initial
        while time.monotonic() < deadline:
            if self._stop_event.is_set():
                return
            time.sleep(1.0)

        consecutive_failures = 0

        while not self._stop_event.is_set():
            # Wait while paused
            while not self._pause_event.is_set():
                if self._stop_event.is_set():
                    return
                time.sleep(1.0)

            try:
                stats = self.store.run_consolidation(project=self.project)
                self._last_run = time.time()
                self._last_stats = stats
                self._run_count += 1
                consecutive_failures = 0
                logger.debug(f"[NeuroSleepNet] Auto sleep complete: {stats}")
            except Exception as e:
                consecutive_failures += 1
                # Exponential backoff: 30s, 60s, 120s, ... capped at 600s (10 min)
                backoff = min(600, 30 * (2 ** (consecutive_failures - 1)))
                logger.error(
                    f"[NeuroSleepNet] Sleep cycle failed "
                    f"(attempt {consecutive_failures}, retrying in {backoff}s): {e}",
                    exc_info=True,
                )
                # Interruptible backoff sleep
                back_deadline = time.monotonic() + backoff
                while time.monotonic() < back_deadline:
                    if self._stop_event.is_set():
                        return
                    time.sleep(1.0)
                continue  # retry without waiting full interval

            # Normal interval sleep, interruptible
            deadline = time.monotonic() + self.interval_seconds
            while time.monotonic() < deadline:
                if self._stop_event.is_set():
                    return
                time.sleep(1.0)

    def _on_exit(self):
        """atexit hook — fires consolidation when process exits cleanly."""
        try:
            logger.info("[NeuroSleepNet] Process exiting — running sleep consolidation (sleep_on_exit)...")
            stats = self.store.run_consolidation(project=self.project)
            
            # V2: Run one-off synthesis on exit if any high-consolidation clusters found
            self._run_synthesis_pass()
            
            self._last_run = time.time()
            self._last_stats = stats
            self._run_count += 1
            logger.info(f"[NeuroSleepNet] Exit consolidation complete: {stats}")
        except Exception as e:
            logger.error(f"[NeuroSleepNet] Exit consolidation failed: {e}")

    def _run_synthesis_pass(self):
        """
        V2: High-level synthesis pass. Finds clusters of episodic memories 
        and prepares them for semantic merging.
        """
        try:
            from neurosleepnet import get_config
            if not get_config().get("synthesis_mode"):
                return
            
            # 1. Fetch episodic memories with high consolidation
            mems = self.store.list_memories(self.project, limit=100)
            episodics = [m for m in mems if m["memory_type"] == "episodic" and m["consolidation_score"] > 0.6]
            
            if len(episodics) < 3:
                return

            clusters = self._cluster_memories(episodics)
            self._synthesize_clusters(clusters)
        except Exception as e:
            logger.debug(f"[NeuroSleepNet V2] Synthesis skipped: {e}")

    def _cluster_memories(self, memories: List[Dict]) -> Dict[str, List[Dict]]:
        """
        P1-1: Group memories by embedding cosine similarity (greedy centroid).
        Threshold 0.78 — tighter than dedup (0.87) to allow thematic clusters.
        Falls back to prefix grouping if embeddings are unavailable.
        """
        import numpy as np
        clusters: List[List[Dict]] = []
        centroids: List[np.ndarray] = []

        for m in memories:
            raw = self.store._get_embedding_blob(m["id"])
            if not raw:
                # No embedding — bucket by first-3-words as last resort
                prefix = " ".join(m["content"].lower().split()[:3])
                placed = False
                for i, cluster in enumerate(clusters):
                    if cluster[0].get("_prefix") == prefix:
                        cluster.append(m)
                        placed = True
                        break
                if not placed:
                    m["_prefix"] = prefix
                    clusters.append([m])
                continue

            emb = np.frombuffer(raw, dtype=np.float32)
            n = np.linalg.norm(emb)
            if n == 0:
                continue
            emb_norm = emb / n

            placed = False
            for i, centroid in enumerate(centroids):
                if float(np.dot(emb_norm, centroid)) > 0.78:
                    clusters[i].append(m)
                    # Update centroid as running mean, re-normalise
                    size = len(clusters[i])
                    new_c = (centroid * (size - 1) + emb_norm) / size
                    nc_norm = np.linalg.norm(new_c)
                    centroids[i] = new_c / nc_norm if nc_norm > 0 else centroid
                    placed = True
                    break
            if not placed:
                clusters.append([m])
                centroids.append(emb_norm)

        # Return as dict keyed by cluster index for compatibility
        return {str(i): c for i, c in enumerate(clusters)}

    def _synthesize_clusters(self, clusters):
        """Perform the actual synthesis and merging of memory clusters."""
        items = clusters.values() if isinstance(clusters, dict) else clusters
        for cluster in items:
            if len(cluster) >= 3:
                ids = [m["id"] for m in cluster]
                if self.synthesizer:
                    try:
                        master_content = self.synthesizer.synthesize(cluster)
                    except Exception as e:
                        logger.warning(f"[NeuroSleepNet V2] Synthesizer failed: {e}")
                        master_content = _jaccard_synthesize(cluster)
                else:
                    master_content = _jaccard_synthesize(cluster)
                self.store.merge_memories(self.project, ids, master_content)
