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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("neurosleepnet.sleep")


class LocalSleepEngine:
    def __init__(self, store, project: Optional[str] = None,
                 interval_seconds: float = 300.0, sleep_on_exit: bool = True):
        self.store = store
        self.project = project
        self.interval_seconds = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default
        self._last_run: Optional[float] = None
        self._last_stats: Dict[str, Any] = {}
        self._run_count = 0
        self._sleep_on_exit = sleep_on_exit

        if sleep_on_exit:
            atexit.register(self._on_exit)

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
            if self._stop_event.is_set(): return
            time.sleep(1.0)

        while not self._stop_event.is_set():
            # Wait if paused
            while not self._pause_event.is_set():
                if self._stop_event.is_set(): return
                time.sleep(1.0)

            try:
                stats = self.store.run_consolidation(project=self.project)
                self._last_run = time.time()
                self._last_stats = stats
                self._run_count += 1
                logger.debug(f"[NeuroSleepNet] Auto sleep complete: {stats}")
            except Exception as e:
                logger.error(f"[NeuroSleepNet] Auto sleep error: {e}")

            # Sleep for interval, interruptible
            deadline = time.monotonic() + self.interval_seconds
            while time.monotonic() < deadline:
                if self._stop_event.is_set(): return
                time.sleep(1.0)

    def _on_exit(self):
        """atexit hook — fires consolidation when process exits cleanly."""
        try:
            logger.info("[NeuroSleepNet] Process exiting — running sleep consolidation (sleep_on_exit)...")
            stats = self.store.run_consolidation(project=self.project)
            
            # V2: Run one-off synthesis on exit if any high-consolidation clusters found
            self._run_experimental_synthesis()
            
            self._last_run = time.time()
            self._last_stats = stats
            self._run_count += 1
            logger.info(f"[NeuroSleepNet] Exit consolidation complete: {stats}")
        except Exception as e:
            logger.error(f"[NeuroSleepNet] Exit consolidation failed: {e}")

    def _run_experimental_synthesis(self):
        """
        V2: Find clusters of episodic memories and 'synthesize' them.
        (Experimental: currently uses a template-based merge if no LLM provided).
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

            # 2. Simple clustering (by first 3 words for now as a V2 preview)
            clusters = {}
            for m in episodics:
                prefix = " ".join(m["content"].lower().split()[:3])
                clusters.setdefault(prefix, []).append(m)
            
            for prefix, cluster in clusters.items():
                if len(cluster) >= 3:
                    logger.info(f"[NeuroSleepNet V2] Synthesizing cluster: {prefix}...")
                    ids = [m["id"] for m in cluster]
                    # In a full LLM impl, we'd call the LLM here.
                    # For now, we use the most recent one as the 'representative' fact.
                    master_content = cluster[0]["content"]
                    self.store.merge_and_synthesize(self.project, ids, master_content)
        except Exception as e:
            logger.debug(f"[NeuroSleepNet V2] Synthesis skipped: {e}")
