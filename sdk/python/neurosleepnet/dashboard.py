"""
dashboard.py — Local dashboard server for NeuroSleepNet Import Mode.

Serves a JSON API and SSE event stream that the React frontend connects to.
Reads directly from SQLite — no Docker, no FastAPI, no external dependencies.
Launched by nsn.dashboard() in a background thread.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import socket
import sqlite3
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("neurosleepnet.dashboard")

# Global event queue for SSE live feed
_event_queue: queue.Queue = queue.Queue(maxsize=500)
_server_instance: Optional["DashboardServer"] = None
_server_port: int = 3000
_server_thread: Optional[threading.Thread] = None


# Global callbacks
_sleep_trigger_cb: Optional[Callable[[], Any]] = None

def set_sleep_trigger(cb: Callable[[], Any]):
    global _sleep_trigger_cb
    _sleep_trigger_cb = cb

def push_event(event_type: str, data: Dict[str, Any]):
    """Push a live event to all SSE subscribers. Called by SDK on remember/recall/pin."""
    try:
        _event_queue.put_nowait({
            "type": event_type,
            "data": data,
            "ts": time.time(),
        })
    except queue.Full:
        pass  # Drop oldest — never block


def _find_free_port(start: int = 3000) -> int:
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    return start


class DashboardHandler(BaseHTTPRequestHandler):
    db_path: str = ""
    project: str = "default"

    def log_message(self, fmt, *args):
        logger.debug(f"[Dashboard] {fmt % args}")
        print(f"[Dashboard] {fmt % args}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)
        project = qs.get("project", [self.project])[0]

        if path.startswith("/api/"):
            if path == "/api/stats":
                self._json(self._get_stats(project))
            elif path == "/api/memories":
                user_id = qs.get("user_id", [None])[0]
                limit = int(qs.get("limit", ["100"])[0])
                self._json(self._get_memories(project, user_id, limit))
            elif path == "/api/pins":
                user_id = qs.get("user_id", [None])[0]
                self._json(self._get_pins(project, user_id))
            elif path == "/api/misses":
                limit = int(qs.get("limit", ["50"])[0])
                self._json(self._get_misses(project, limit))
            elif path == "/api/sleep":
                limit = int(qs.get("limit", ["20"])[0])
                self._json(self._get_sleep_log(project, limit))
            elif path == "/api/events":
                self._sse()
            elif path == "/api/health":
                self._json({"status": "ok", "project": project, "port": _server_port})
            else:
                self.send_response(404)
                self._cors()
                self.end_headers()
        else:
            # Serve static frontend files
            self._serve_static(parsed.path)

    def _serve_static(self, path: str):
        # Default to index.html for SPA routing
        if path == "/" or path == "" or "." not in path.split("/")[-1]:
            path = "/index.html"
        
        # Look for frontend files inside the package
        base_dir = os.path.join(os.path.dirname(__file__), "frontend")
        file_path = os.path.join(base_dir, path.lstrip("/"))
        
        if not os.path.exists(file_path):
            # Fallback to index.html for React Router
            file_path = os.path.join(base_dir, "index.html")

        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            return

        # Content types
        ext = os.path.splitext(file_path)[1]
        content_type = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
        }.get(ext, "application/octet-stream")

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._cors()
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)
        project = qs.get("project", [self.project])[0]

        if path == "/api/memories":
            mid = qs.get("id", [None])[0]
            if mid:
                self._delete_memory(mid, project)
                self._json({"deleted": True, "id": mid})
            else:
                self._json({"error": "id required"})
        elif path == "/api/pins":
            mid = qs.get("id", [None])[0]
            if mid:
                self._unpin_memory(mid, project)
                self._json({"unpinned": True, "id": mid})
            else:
                self._json({"error": "id required"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        
        if path == "/api/sleep":
            if _sleep_trigger_cb:
                _sleep_trigger_cb()
                self._json({"status": "triggered"})
            else:
                self._json({"status": "error", "message": "Sleep engine not connected"}, status=500)
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()
        # Drain stale events first
        while not _event_queue.empty():
            try:
                _event_queue.get_nowait()
            except queue.Empty:
                break
        try:
            while True:
                try:
                    event = _event_queue.get(timeout=15)
                    msg = f"data: {json.dumps(event, default=str)}\n\n"
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _get_stats(self, project: str) -> Dict:
        try:
            with self._conn() as c:
                total = c.execute("SELECT COUNT(*) FROM memories WHERE project=? AND status='active'", (project,)).fetchone()[0]
                archived = c.execute("SELECT COUNT(*) FROM memories WHERE project=? AND status='archived'", (project,)).fetchone()[0]
                pinned = c.execute("SELECT COUNT(*) FROM memories WHERE project=? AND pinned=1 AND status='active'", (project,)).fetchone()[0]
                avg_score = c.execute("SELECT AVG(consolidation_score) FROM memories WHERE project=? AND status='active'", (project,)).fetchone()[0] or 0.0
                miss_count = c.execute("SELECT COUNT(*) FROM miss_log WHERE project=?", (project,)).fetchone()[0]
                sleep_cycles = c.execute("SELECT COUNT(*) FROM sleep_log WHERE project=?", (project,)).fetchone()[0]
                users = c.execute("SELECT COUNT(DISTINCT user_id) FROM memories WHERE project=? AND user_id IS NOT NULL", (project,)).fetchone()[0]
                by_type_rows = c.execute("SELECT memory_type, COUNT(*) as cnt FROM memories WHERE project=? AND status='active' GROUP BY memory_type", (project,)).fetchall()
                by_type = {r["memory_type"]: r["cnt"] for r in by_type_rows}

                # Miss rate
                recall_attempts = c.execute("SELECT COUNT(*) FROM miss_log WHERE project=?", (project,)).fetchone()[0]
                hit_count = total  # approximate

                # Health score: freshness × recall accuracy × dedup ratio
                # Simple: avg_consolidation_score weighted by activity
                health_score = round(min(1.0, avg_score * 1.2), 2)

                # Anomaly: rising miss rate (last 1h vs prior 1h)
                recent_misses = c.execute(
                    "SELECT COUNT(*) FROM miss_log WHERE project=? AND created_at >= strftime('%Y-%m-%d %H:%M:%S','now','-1 hour')", (project,)
                ).fetchone()[0]
                prior_misses = c.execute(
                    "SELECT COUNT(*) FROM miss_log WHERE project=? AND created_at < strftime('%Y-%m-%d %H:%M:%S','now','-1 hour') AND created_at >= strftime('%Y-%m-%d %H:%M:%S','now','-2 hours')", (project,)
                ).fetchone()[0]
                anomaly_miss_spike = recent_misses > max(3, prior_misses * 1.5)

                last_sleep = c.execute("SELECT finished_at, boosted, decayed, archived, deduped, promoted FROM sleep_log WHERE project=? ORDER BY finished_at DESC LIMIT 1", (project,)).fetchone()

            return {
                "project": project,
                "total_memories": total,
                "archived": archived,
                "pinned": pinned,
                "unique_users": users,
                "by_type": by_type,
                "avg_consolidation_score": round(avg_score, 3),
                "health_score": health_score,
                "miss_count": miss_count,
                "sleep_cycles_run": sleep_cycles,
                "anomaly_miss_spike": anomaly_miss_spike,
                "recent_misses_1h": recent_misses,
                "last_sleep": dict(last_sleep) if last_sleep else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_memories(self, project: str, user_id: Optional[str], limit: int) -> List[Dict]:
        try:
            with self._conn() as c:
                user_clause = " AND user_id=?" if user_id else ""
                user_params = [user_id] if user_id else []
                rows = c.execute(
                    f"SELECT id, content, memory_type, user_id, importance, consolidation_score, feedback_score, access_count, pinned, label, status, created_at, last_accessed_at FROM memories WHERE project=? AND status='active'{user_clause} ORDER BY created_at DESC LIMIT ?",
                    [project] + user_params + [limit]
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    def _get_pins(self, project: str, user_id: Optional[str]) -> List[Dict]:
        try:
            with self._conn() as c:
                user_clause = " AND (user_id=? OR user_id IS NULL)" if user_id else ""
                user_params = [user_id] if user_id else []
                rows = c.execute(
                    f"SELECT id, content, label, user_id, importance, created_at FROM memories WHERE project=? AND pinned=1 AND status='active'{user_clause} ORDER BY created_at DESC",
                    [project] + user_params
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    def _get_misses(self, project: str, limit: int) -> List[Dict]:
        try:
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id, query, memory_content, score, threshold, reason, user_id, created_at FROM miss_log WHERE project=? ORDER BY created_at DESC LIMIT ?",
                    (project, limit)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    def _get_sleep_log(self, project: str, limit: int) -> List[Dict]:
        try:
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id, project, boosted, decayed, archived, deduped, promoted, started_at, finished_at FROM sleep_log WHERE project=? ORDER BY finished_at DESC LIMIT ?",
                    (project, limit)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    def _delete_memory(self, memory_id: str, project: str):
        try:
            with self._conn() as c:
                c.execute("DELETE FROM memories WHERE id=? AND project=?", (memory_id, project))
                c.commit()
        except Exception:
            pass

    def _unpin_memory(self, memory_id: str, project: str):
        try:
            with self._conn() as c:
                c.execute("UPDATE memories SET pinned=0 WHERE id=? AND project=?", (memory_id, project))
                c.commit()
        except Exception:
            pass


class DashboardServer(HTTPServer):
    pass


def start_local_server(db_path: str, project: str, port: int = 3000) -> int:
    """Start local dashboard HTTP server in a background daemon thread. Returns port."""
    global _server_instance, _server_port, _server_thread

    if _server_thread and _server_thread.is_alive():
        return _server_port

    actual_port = _find_free_port(port)
    _server_port = actual_port

    # Inject config into handler class
    handler = type("Handler", (DashboardHandler,), {
        "db_path": db_path,
        "project": project,
    })

    server = DashboardServer(("", actual_port), handler)
    _server_instance = server

    def _run():
        logger.debug(f"[NeuroSleepNet] Local dashboard server running on :{actual_port}")
        server.serve_forever()

    _server_thread = threading.Thread(target=_run, daemon=True, name="NSN-Dashboard")
    _server_thread.start()
    return actual_port


def open_dashboard(project: str, port: int, open_browser: bool = True):
    """Print dashboard URL and optionally open in browser."""
    proj_slug = project[:8]
    url = f"http://localhost:{port}/p/{proj_slug}"
    print(f"[NeuroSleepNet] Dashboard → {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
