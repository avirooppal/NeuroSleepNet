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
        # P2-5: logger.debug is sufficient — remove print() that spammed every asset request
        logger.debug(f"[Dashboard] {fmt % args}")

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
        
        # 1. Resolve project
        project_param = qs.get("project", qs.get("project_id", [self.project]))[0]
        all_projs = self._get_all_projects()
        project = next((p for p in all_projs if p == project_param or p.startswith(project_param)), project_param)
        
        # 2. API Routing
        api_path = path[4:] if path.startswith("/v1/") else (path[5:] if path.startswith("/api/") else None)
        
        if api_path:
            # Route to handlers
            if api_path == "stats":
                return self._json(self._get_stats(project))
            if api_path in ("memories", "memories/retrieve"):
                user_id = qs.get("user_id", [None])[0]
                limit = int(qs.get("limit", ["100"])[0])
                mems = self._get_memories(project, user_id, limit)
                return self._json({"memories": mems} if api_path == "memories/retrieve" else mems)
            if api_path == "pins":
                return self._json(self._get_pins(project, qs.get("user_id", [None])[0]))
            if api_path == "misses":
                return self._json(self._get_misses(project, int(qs.get("limit", ["50"])[0])))
            if api_path == "sleep":
                return self._json(self._get_sleep_log(project, int(qs.get("limit", ["20"])[0])))
            if api_path == "events":
                return self._sse()
            if api_path == "health":
                return self._json({"status": "ok", "project": project, "port": _server_port})
            if api_path == "projects":
                return self._json([{"id": p, "name": p} for p in all_projs])
            if api_path == "benchmark":
                return self._json(self._get_mock_benchmarks()) # Still mock for now
            if api_path.startswith("benchmark/"):
                return self._json(self._get_mock_benchmarks()[0])
            if api_path == "analytics/attention":
                return self._json(self._get_attention_data(project))
            if api_path == "analytics/pathway-map":
                return self._json(self._get_pathway_map(project))
            
            self.send_response(404)
            self._cors()
            self.end_headers()
            return

        # 3. Static Files
        self._serve_static(path)

    def _get_mock_benchmarks(self) -> List[Dict]:
        return [{
            "id": "bench-1", "model": "llama3.2:1b", "scenario": "recall",
            "status": "completed", "score": 0.85, "control_score": 0.32,
            "run_key": "seed-123", "created_at": "2024-05-03"
        }]

    def _get_attention_data(self, project: str) -> List[Dict]:
        try:
            with self._conn(project) as c:
                rows = c.execute(
                    "SELECT memory_type, COUNT(*) as count FROM memories WHERE project=? GROUP BY memory_type",
                    (project,)
                ).fetchall()
                if not rows:
                    return [{"type": "Semantic", "recalls": 0}]
                return [{"type": r["memory_type"].capitalize(), "recalls": r["count"]} for r in rows]
        except Exception:
            return []

    def _get_pathway_map(self, project: str) -> Dict:
        # Simplified: top 10 memories as nodes, no links for now (requires embedding similarity matrix)
        try:
            with self._conn(project) as c:
                rows = c.execute(
                    "SELECT id, content, memory_type, feedback_score, importance FROM memories WHERE project=? LIMIT 10",
                    (project,)
                ).fetchall()
                nodes = []
                for r in rows:
                    nodes.append({
                        "id": r["id"], "content": r["content"][:60], "type": r["memory_type"],
                        "feedback": r["feedback_score"] or 0.0, "importance": r["importance"] or 1.0, "size": 10
                    })
                return {"nodes": nodes, "links": []}
        except Exception:
            return {"nodes": [], "links": []}

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
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass
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
        elif path == "/api/benchmark/run":
            self._json({"run_id": "bench-" + str(int(time.time())), "status": "started"})
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
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

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

    def _conn(self, project: str = None):
        # Dynamically get the DB path if possible, else fallback to injected
        from neurosleepnet import get_config
        cfg = get_config()
        p = project or self.project
        if cfg and cfg.get("data_dir"):
            db_file = os.path.join(cfg["data_dir"], "neurosleepnet.db")
            c = sqlite3.connect(db_file, timeout=10)
        else:
            c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _get_stats(self, project: str) -> Dict:
        try:
            with self._conn(project) as c:
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
            with self._conn(project) as c:
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
            with self._conn(project) as c:
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
            with self._conn(project) as c:
                rows = c.execute(
                    "SELECT id, query, memory_content, score, threshold, reason, user_id, created_at FROM miss_log WHERE project=? ORDER BY created_at DESC LIMIT ?",
                    (project, limit)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    def _get_all_projects(self) -> List[str]:
        try:
            with self._conn() as c:
                rows = c.execute("SELECT DISTINCT project FROM memories").fetchall()
                return [r[0] for r in rows]
        except Exception:
            return [self.project]

    def _get_sleep_log(self, project: str, limit: int) -> List[Dict]:
        try:
            with self._conn(project) as c:
                rows = c.execute(
                    "SELECT id, project, boosted, decayed, archived, deduped, promoted, started_at, finished_at FROM sleep_log WHERE project=? ORDER BY finished_at DESC LIMIT ?",
                    (project, limit)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    def _delete_memory(self, memory_id: str, project: str):
        try:
            with self._conn(project) as c:
                c.execute("DELETE FROM memories WHERE id=? AND project=?", (memory_id, project))
                c.commit()
        except Exception:
            pass

    def _unpin_memory(self, memory_id: str, project: str):
        try:
            with self._conn(project) as c:
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
    
    # Fix 7: Colab-aware dashboard URL
    is_colab = False
    try:
        import google.colab
        is_colab = True
    except ImportError:
        pass

    if is_colab:
        try:
            from google.colab.output import proxy_port
            url = f"https://localhost:{port}/p/{proj_slug}"
            print(f"[NeuroSleepNet] Dashboard (Colab) → {url}")
            print(f"[NeuroSleepNet] Note: Use the 'proxy_port' helper if the link doesn't open.")
        except Exception:
            url = f"http://localhost:{port}/p/{proj_slug}"
            print(f"[NeuroSleepNet] Dashboard → {url}")
    else:
        url = f"http://localhost:{port}/p/{proj_slug}"
        print(f"[NeuroSleepNet] Dashboard → {url}")
        if open_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass

def serve_dashboard_cli(db_path: str, project: str, port: int = 3000):
    """Start local dashboard HTTP server in foreground (blocking)."""
    actual_port = _find_free_port(port)
    
    # Inject config into handler class
    handler = type("Handler", (DashboardHandler,), {
        "db_path": db_path,
        "project": project,
    })

    server = DashboardServer(("", actual_port), handler)
    proj_slug = project[:8]
    url = f"http://localhost:{actual_port}/p/{proj_slug}"
    
    print("="*60)
    print("  NeuroSleepNet Local Dashboard  ")
    print("="*60)
    print(f"  Project:   {project}")
    print(f"  Database:  {db_path}")
    print(f"  URL:       {url}")
    print("="*60)
    print("\nPress Ctrl+C to stop the server.\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Dashboard server stopped.")
