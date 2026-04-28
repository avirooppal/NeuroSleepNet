"""
Local sleep engine for NeuroSleepNet.
Runs background memory consolidation in a daemon thread.
"""
import logging
import threading
import time
from typing import Dict, Any

from .local_store import LocalStore

logger = logging.getLogger("neurosleepnet.sleep")

class LocalSleepEngine:
    def __init__(self, store: LocalStore, interval_hours: float = 6.0):
        self.store = store
        self.interval_seconds = interval_hours * 3600
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="NSNSleepThread")
            self._thread.start()
            logger.info(f"[NSN] Local sleep engine started (interval: {self.interval_seconds/3600:.1f}h)")

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread.join(timeout=2.0)

    def run_now(self) -> Dict[str, Any]:
        """Manually trigger memory consolidation."""
        logger.info("[NSN] Running manual memory consolidation...")
        try:
            stats = self.store.run_consolidation()
            logger.info(f"[NSN] Consolidation complete: {stats}")
            return stats
        except Exception as e:
            logger.error(f"[NSN] Consolidation failed: {e}")
            return {"error": str(e)}

    def _run_loop(self):
        # Initial sleep before first run (don't run immediately on boot)
        initial_wait = min(300, self.interval_seconds) # Wait at least 5 mins or interval
        for _ in range(int(initial_wait)):
            if self._stop_event.is_set():
                return
            time.sleep(1)
            
        while not self._stop_event.is_set():
            try:
                self.store.run_consolidation()
            except Exception as e:
                logger.error(f"[NSN] Background consolidation error: {e}")
                
            # Sleep for the interval, checking stop event periodically
            for _ in range(int(self.interval_seconds)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
