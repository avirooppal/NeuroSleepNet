"""
LocalStore — SQLite-backed persistent memory for NeuroSleepNet (Import Mode).
"""
import json, logging, os, re, sqlite3, uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger("neurosleepnet.store")


class LocalStore:
    def __init__(self, data_dir: str = "~/.neurosleepnet"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "neurosleepnet.db")
        self._init_db()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=30.0)
        c.row_factory = sqlite3.Row
        return c

    def _add_column_if_missing(self, table: str, column: str, definition: str):
        with self._conn() as c:
            cur = c.cursor()
            try:
                cur.execute(f"SELECT {column} FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                c.commit()

    def _init_db(self):
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    user_id TEXT,
                    agent_id TEXT,
                    session_id TEXT,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'episodic',
                    tags TEXT DEFAULT '[]',
                    importance REAL DEFAULT 1.0,
                    consolidation_score REAL DEFAULT 0.5,
                    feedback_score REAL DEFAULT 0.0,
                    feedback_count INTEGER DEFAULT 0,
                    access_count INTEGER DEFAULT 0,
                    pinned INTEGER DEFAULT 0,
                    label TEXT,
                    status TEXT DEFAULT 'active',
                    version INTEGER DEFAULT 1,
                    deprecated_by TEXT,
                    embedding BLOB,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
                    last_accessed_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
                    last_consolidated_at TEXT,
                    expires_at TEXT
                );

                CREATE TABLE IF NOT EXISTS miss_log (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    user_id TEXT,
                    query TEXT NOT NULL,
                    memory_id TEXT,
                    memory_content TEXT,
                    score REAL,
                    threshold REAL,
                    reason TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now'))
                );

                CREATE TABLE IF NOT EXISTS sleep_log (
                    id TEXT PRIMARY KEY,
                    project TEXT,
                    boosted INTEGER DEFAULT 0,
                    decayed INTEGER DEFAULT 0,
                    archived INTEGER DEFAULT 0,
                    deduped INTEGER DEFAULT 0,
                    promoted INTEGER DEFAULT 0,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS project_meta (
                    project TEXT PRIMARY KEY,
                    first_run INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
                    token_savings INTEGER DEFAULT 0,
                    settings TEXT DEFAULT '{}'
                );
            """)
            # FTS
            cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, content='memories', content_rowid='rowid')")
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories
                BEGIN INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content); END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories
                BEGIN INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content); END;
            """)
        
        # Migrations for existing DBs
        cols = {
            "user_id": "TEXT",
            "project": "TEXT NOT NULL DEFAULT 'default'",
            "agent_id": "TEXT",
            "session_id": "TEXT",
            "memory_type": "TEXT DEFAULT 'episodic'",
            "tags": "TEXT DEFAULT '[]'",
            "importance": "REAL DEFAULT 1.0",
            "consolidation_score": "REAL DEFAULT 0.5",
            "feedback_score": "REAL DEFAULT 0.0",
            "feedback_count": "INTEGER DEFAULT 0",
            "access_count": "INTEGER DEFAULT 0",
            "pinned": "INTEGER DEFAULT 0",
            "label": "TEXT",
            "status": "TEXT DEFAULT 'active'",
            "version": "INTEGER DEFAULT 1",
            "deprecated_by": "TEXT",
            "embedding": "BLOB",
            "last_accessed_at": "TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now'))",
            "last_consolidated_at": "TEXT",
            "expires_at": "TEXT"
        }
        for col, definition in cols.items():
            self._add_column_if_missing("memories", col, definition)
        
        self._add_column_if_missing("project_meta", "settings", "TEXT DEFAULT '{}'")

        # Post-migration indices
        with self._conn() as c:
            c.execute("CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(project, user_id, status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_mem_proj ON memories(project, status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_mem_pinned ON memories(project, pinned, status)")
            c.commit()

    # ── helpers ────────────────────────────────────────────────────────────────

    def _sanitize(self, content: str) -> str:
        content = re.sub(r'<[^>]*?>', '', content)
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', content)
        return content.strip()

    def _is_first_run(self, project: str) -> bool:
        with self._conn() as c:
            row = c.execute("SELECT first_run FROM project_meta WHERE project=?", (project,)).fetchone()
            if row is None:
                c.execute("INSERT INTO project_meta(project) VALUES(?)", (project,))
                c.commit()
                return True
            return bool(row["first_run"])

    def mark_seen(self, project: str):
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO project_meta(project) VALUES(?)", (project,))
            c.execute("UPDATE project_meta SET first_run=0 WHERE project=?", (project,))
            c.commit()

    # ── store ──────────────────────────────────────────────────────────────────

    def store(self, content: str, project: str, user_id: Optional[str] = None,
              agent_id: Optional[str] = None, session_id: Optional[str] = None,
              tags: List[str] = None, importance: float = 1.0,
              memory_type: str = "episodic", embedding: List[float] = None,
              ttl_days: Optional[int] = None, pinned: bool = False,
              label: Optional[str] = None) -> str:

        content = self._sanitize(content)
        mid = str(uuid.uuid4())
        emb_blob = np.array(embedding, dtype=np.float32).tobytes() if embedding else None
        expires_at = None
        if ttl_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).strftime("%Y-%m-%d %H:%M:%S")

        with self._conn() as c:
            cur = c.cursor()

            # Conflict resolution — deprecate semantically similar active memories (skip for pinned)
            if not pinned and embedding:
                q = np.array(embedding, dtype=np.float32)
                qn = np.linalg.norm(q)
                if qn > 0:
                    q = q / qn
                    rows = cur.execute(
                        "SELECT id, embedding FROM memories WHERE project=? AND status='active' AND pinned=0 AND embedding IS NOT NULL",
                        (project,)
                    ).fetchall()
                    for row in rows:
                        m_emb = np.frombuffer(row["embedding"], dtype=np.float32)
                        mn = np.linalg.norm(m_emb)
                        if mn == 0: continue
                        sim = float(np.dot(q, m_emb / mn))
                        if sim > 0.88:
                            cur.execute("UPDATE memories SET status='deprecated', deprecated_by=? WHERE id=?", (mid, row["id"]))

            cur.execute("""
                INSERT INTO memories
                    (id, project, user_id, agent_id, session_id, content, memory_type,
                     tags, importance, embedding, expires_at, pinned, label)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (mid, project, user_id, agent_id, session_id, content, memory_type,
                  json.dumps(tags or []), importance, emb_blob, expires_at,
                  1 if pinned else 0, label))
            c.commit()
        return mid

    # ── retrieve ───────────────────────────────────────────────────────────────

    def _normalize_recency(self, created_at_str: str) -> float:
        """Port of attention.py normalize_recency for local store."""
        import math
        try:
            created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - created_at
            hours = max(0, delta.total_seconds() / 3600.0)
            return 1.0 / (1.0 + math.log(1 + hours))
        except:
            return 0.5

    def _score_memory(self, similarity: float, recency: float, consolidation: float, 
                      feedback: float, importance: float, weights: dict) -> float:
        """Port of attention.py score_memory for local store."""
        w = weights
        base_score = (
            (similarity * w.get("w_sim", 0.45)) +
            (recency * w.get("w_rec", 0.15)) +
            (consolidation * w.get("w_con", 0.25)) +
            (feedback * w.get("w_fb", 0.15))
        )
        return base_score * importance

    def retrieve(self, query: str, query_embedding: Optional[List[float]], project: str,
                 user_id: Optional[str] = None, top_k: int = 5,
                 memory_types: Optional[List[str]] = None,
                 min_score: float = 0.0,
                 tfidf_index=None) -> List[Dict[str, Any]]:

        use_dense = bool(query_embedding)
        if use_dense:
            q_emb = np.array(query_embedding, dtype=np.float32)
            qn = np.linalg.norm(q_emb)
            if qn > 0: q_emb = q_emb / qn
        else:
            q_emb = None
            qn = 0.0

        # TF-IDF fallback scores keyed by memory_id
        tfidf_scores: Dict[str, float] = {}
        if not use_dense and tfidf_index is not None:
            for mid, score in tfidf_index.query(query, top_k=top_k * 4):
                tfidf_scores[mid] = score

        results: Dict[str, Dict] = {}

        with self._conn() as c:
            cur = c.cursor()

            # Base filter
            type_clause = ""
            type_params: list = []
            if memory_types:
                placeholders = ",".join("?" * len(memory_types))
                type_clause = f" AND memory_type IN ({placeholders})"
                type_params = list(memory_types)

            user_clause = " AND (user_id=? OR user_id IS NULL)" if user_id else ""
            user_params = [user_id] if user_id else []

            # 0. Load project settings (weights)
            settings_row = cur.execute("SELECT settings FROM project_meta WHERE project=?", (project,)).fetchone()
            weights = {"w_sim": 0.45, "w_rec": 0.15, "w_con": 0.25, "w_fb": 0.15}
            if settings_row:
                try:
                    p_settings = json.loads(settings_row[0])
                    weights = p_settings.get("attention_weights", weights)
                except:
                    pass

            # 1. Pinned memories — always injected first
            pin_rows = cur.execute(
                f"SELECT * FROM memories WHERE project=? AND pinned=1 AND status='active'{user_clause}",
                [project] + user_params
            ).fetchall()
            for row in pin_rows:
                d = dict(row)
                d["tags"] = json.loads(d.get("tags") or "[]")
                d["attention_score"] = 1.0
                d["pinned"] = True
                d.pop("embedding", None)
                results[d["id"]] = d

            # 2. FTS keyword signal
            STOP = {"what","where","when","how","the","and","for","with","from","that","this"}
            tokens = [t.lower() for t in query.split() if len(t) > 3 and t.lower() not in STOP]
            if tokens:
                fts_q = " OR ".join(tokens)
                try:
                    fts_rows = cur.execute(f"""
                        SELECT m.id, bm25(memories_fts) as rank
                        FROM memories_fts fts
                        JOIN memories m ON m.rowid = fts.rowid
                        WHERE memories_fts MATCH ? AND m.project=? AND m.status='active'
                        {type_clause}
                    """, [fts_q, project] + type_params).fetchall()
                    for row in fts_rows:
                        results.setdefault(row["id"], {})["keyword_score"] = 1.0 / (1.0 + abs(row["rank"]))
                except Exception:
                    pass

            # 3. Semantic / TF-IDF signal
            emb_filter = "AND embedding IS NOT NULL" if use_dense else ""
            sem_rows = cur.execute(f"""
                SELECT id, content, tags, importance, consolidation_score, feedback_score,
                       memory_type, created_at, pinned, label, embedding
                FROM memories
                WHERE project=? AND status='active' {emb_filter}
                {type_clause}{user_clause}
            """, [project] + type_params + user_params).fetchall()

            now = datetime.now(timezone.utc)
            for row in sem_rows:
                d = dict(row)
                mid = d["id"]
                if mid in results and results[mid].get("pinned"): continue

                if use_dense:
                    m_emb = np.frombuffer(d.pop("embedding"), dtype=np.float32)
                    mn = np.linalg.norm(m_emb)
                    cosine = float(np.dot(q_emb, m_emb / mn)) if mn > 0 and qn > 0 else 0.0
                else:
                    d.pop("embedding", None)
                    cosine = 0.0

                # Use _normalize_recency from local_store (already handles hours/log scale)
                recency = self._normalize_recency(d["created_at"])

                k_score = results.get(mid, {}).get("keyword_score", 0.0)
                tfidf_score = tfidf_scores.get(mid, 0.0)

                # Similarity is either cosine (dense) or tfidf (sparse) or keyword
                sim = cosine if use_dense else max(tfidf_score, k_score)

                attention = self._score_memory(
                    similarity=sim,
                    recency=recency,
                    consolidation=d.get("consolidation_score", 0.5),
                    feedback=d.get("feedback_score", 0.5),
                    importance=d.get("importance", 1.0),
                    weights=weights
                )

                if attention < min_score:
                    continue

                d.update({
                    "attention_score": round(attention, 4),
                    "similarity": round(cosine, 4),
                    "keyword_score": round(k_score, 4),
                    "tags": json.loads(d.get("tags") or "[]"),
                    "pinned": bool(d.get("pinned", 0)),
                })
                results[mid] = d

            # Sort: pinned first, then by attention score
            final = sorted(
                [v for v in results.values() if "attention_score" in v],
                key=lambda x: (x.get("pinned", False), x["attention_score"]),
                reverse=True
            )
            top = final[:top_k]

            if top:
                ids = [m["id"] for m in top if not m.get("pinned")]
                if ids:
                    cur.execute(
                        f"UPDATE memories SET access_count=access_count+1, last_accessed_at=strftime('%Y-%m-%d %H:%M:%S','now') WHERE id IN ({','.join('?'*len(ids))})",
                        ids
                    )
                c.commit()

            # Fix 4: Update token_savings estimate.
            # Savings = tokens in all candidate memories - tokens in injected top-k subset.
            all_candidates_tokens = sum(len(v.get("content", "")) // 4 for v in final)
            injected_tokens = sum(len(m.get("content", "")) // 4 for m in top)
            savings_delta = max(0, all_candidates_tokens - injected_tokens)
            if savings_delta > 0:
                cur.execute(
                    "UPDATE project_meta SET token_savings = COALESCE(token_savings, 0) + ? WHERE project=?",
                    (savings_delta, project)
                )
                c.commit()

            return top

    # ── text search (no embedding) ─────────────────────────────────────────────

    def search_text(self, query: str, project: str, user_id: Optional[str] = None,
                    top_k: int = 10) -> List[Dict[str, Any]]:
        with self._conn() as c:
            user_clause = " AND (user_id=? OR user_id IS NULL)" if user_id else ""
            user_params = [user_id] if user_id else []
            rows = c.execute(f"""
                SELECT m.* FROM memories_fts fts
                JOIN memories m ON m.rowid = fts.rowid
                WHERE memories_fts MATCH ? AND m.project=? AND m.status='active'{user_clause}
                LIMIT ?
            """, [query, project] + user_params + [top_k]).fetchall()
            out = []
            for row in rows:
                d = dict(row)
                d["tags"] = json.loads(d.get("tags") or "[]")
                d.pop("embedding", None)
                d["attention_score"] = 0.5
                out.append(d)
            return out

    # ── pin management ─────────────────────────────────────────────────────────

    def pin_memory(self, content: str, project: str, user_id: Optional[str],
                   label: Optional[str], embedding: List[float] = None) -> str:
        return self.store(content=content, project=project, user_id=user_id,
                          memory_type="semantic", pinned=True, label=label,
                          importance=1.0, embedding=embedding)

    def unpin_memory(self, memory_id: str, project: str) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "UPDATE memories SET pinned=0 WHERE id=? AND project=? AND pinned=1",
                (memory_id, project)
            )
            c.commit()
            return cur.rowcount > 0

    def list_pins(self, project: str, user_id: Optional[str] = None) -> List[Dict]:
        with self._conn() as c:
            user_clause = " AND (user_id=? OR user_id IS NULL)" if user_id else ""
            user_params = [user_id] if user_id else []
            rows = c.execute(
                f"SELECT id, content, label, user_id, created_at FROM memories WHERE project=? AND pinned=1 AND status='active'{user_clause}",
                [project] + user_params
            ).fetchall()
            return [dict(r) for r in rows]

    # ── forget ────────────────────────────────────────────────────────────────

    def forget_by_id(self, memory_id: str, project: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM memories WHERE id=? AND project=?", (memory_id, project))
            c.commit()
            return cur.rowcount > 0

    def forget_user(self, user_id: str, project: str) -> int:
        with self._conn() as c:
            cur = c.execute("DELETE FROM memories WHERE user_id=? AND project=?", (user_id, project))
            c.commit()
            return cur.rowcount

    def forget_project(self, project: str) -> int:
        with self._conn() as c:
            cur = c.execute("DELETE FROM memories WHERE project=?", (project,))
            c.commit()
            return cur.rowcount

    # ── list / search ──────────────────────────────────────────────────────────

    def list_memories(self, project: str, user_id: Optional[str] = None,
                      limit: int = 50) -> List[Dict]:
        with self._conn() as c:
            user_clause = " AND user_id=?" if user_id else ""
            user_params = [user_id] if user_id else []
            rows = c.execute(
                f"SELECT id, content, memory_type, importance, consolidation_score, access_count, pinned, label, created_at, user_id FROM memories WHERE project=? AND status='active'{user_clause} ORDER BY created_at DESC LIMIT ?",
                [project] + user_params + [limit]
            ).fetchall()
            return [dict(r) for r in rows]

    # ── feedback ───────────────────────────────────────────────────────────────

    def update_feedback(self, memory_id: str, project: str, helpful: bool) -> bool:
        delta = 0.1 if helpful else -0.05
        with self._conn() as c:
            cur = c.execute("""
                UPDATE memories
                SET feedback_score = MAX(-1.0, MIN(1.0, feedback_score + ?)),
                    feedback_count = feedback_count + 1
                WHERE id=? AND project=?
            """, (delta, memory_id, project))
            c.commit()
            return cur.rowcount > 0

    # ── miss log ───────────────────────────────────────────────────────────────

    def log_miss(self, project: str, query: str, score: float, threshold: float,
                 memory_id: Optional[str] = None, memory_content: Optional[str] = None,
                 user_id: Optional[str] = None, reason: str = "below_threshold"):
        with self._conn() as c:
            c.execute("""
                INSERT INTO miss_log (id, project, user_id, query, memory_id, memory_content, score, threshold, reason)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (str(uuid.uuid4()), project, user_id, query, memory_id, memory_content, score, threshold, reason))
            c.commit()

    def get_misses(self, project: str, limit: int = 50) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM miss_log WHERE project=? ORDER BY created_at DESC LIMIT ?",
                (project, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── stats ──────────────────────────────────────────────────────────────────

    def get_stats(self, project: str) -> Dict[str, Any]:
        with self._conn() as c:
            total = c.execute(
                "SELECT COUNT(*) FROM memories WHERE project=? AND status='active'",
                (project,)
            ).fetchone()[0]

            by_type = {}
            for row in c.execute(
                "SELECT memory_type, COUNT(*) as cnt FROM memories WHERE project=? AND status='active' GROUP BY memory_type",
                (project,)
            ):
                by_type[row["memory_type"]] = row["cnt"]

            pinned = c.execute(
                "SELECT COUNT(*) FROM memories WHERE project=? AND pinned=1 AND status='active'",
                (project,)
            ).fetchone()[0]

            avg_score = c.execute(
                "SELECT AVG(consolidation_score) FROM memories WHERE project=? AND status='active'",
                (project,)
            ).fetchone()[0] or 0.0

            # Fix 4: rename 'hits' → 'miss_count' (was querying miss_log, not hits)
            miss_count = c.execute(
                "SELECT COUNT(*) FROM miss_log WHERE project=?",
                (project,)
            ).fetchone()[0]

            # Hit count: sum of access_count across all active memories (approximation)
            recall_hit_count = c.execute(
                "SELECT COALESCE(SUM(access_count), 0) FROM memories WHERE project=? AND status='active'",
                (project,)
            ).fetchone()[0] or 0

            total_recalls = recall_hit_count + miss_count
            recall_hit_rate = (
                round(recall_hit_count / total_recalls, 3) if total_recalls > 0 else 0.0
            )
            recall_miss_rate = (
                round(miss_count / total_recalls, 3) if total_recalls > 0 else 0.0
            )

            # Fix 4: token_savings from project_meta (now updated by retrieve())
            token_savings_row = c.execute(
                "SELECT COALESCE(token_savings, 0) FROM project_meta WHERE project=?",
                (project,)
            ).fetchone()
            token_savings = token_savings_row[0] if token_savings_row else 0

            sleep_cycles = c.execute(
                "SELECT COUNT(*) FROM sleep_log WHERE project=?",
                (project,)
            ).fetchone()[0]

            memories_consolidated = c.execute(
                "SELECT COALESCE(SUM(boosted), 0) FROM sleep_log WHERE project=?",
                (project,)
            ).fetchone()[0] or 0

            dupes_removed = c.execute(
                "SELECT COALESCE(SUM(deduped), 0) FROM sleep_log WHERE project=?",
                (project,)
            ).fetchone()[0] or 0

            users = c.execute(
                "SELECT COUNT(DISTINCT user_id) FROM memories WHERE project=? AND user_id IS NOT NULL",
                (project,)
            ).fetchone()[0]

        return {
            "total_memories": total,
            "by_type": by_type,
            "pinned": pinned,
            "avg_consolidation_score": round(float(avg_score), 3),
            "health_score": round(min(1.0, float(avg_score) * 1.2), 2),
            "miss_count": miss_count,
            "recall_hit_count": recall_hit_count,
            "recall_hit_rate": recall_hit_rate,
            "recall_miss_rate": recall_miss_rate,
            "token_savings_estimate": token_savings,
            "sleep_cycles_run": sleep_cycles,
            "memories_consolidated": memories_consolidated,
            "dupes_removed": dupes_removed,
            "unique_users": users,
        }

    # ── export / import ────────────────────────────────────────────────────────

    def export_all(self, project: str) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, content, memory_type, user_id, tags, importance, consolidation_score, pinned, label, created_at, embedding FROM memories WHERE project=? AND status='active'",
                (project,)
            ).fetchall()
            out = []
            for row in rows:
                d = dict(row)
                d["tags"] = json.loads(d.get("tags") or "[]")
                if d.get("embedding"):
                    # Convert blob back to list for JSON compatibility
                    d["embedding"] = np.frombuffer(d["embedding"], dtype=np.float32).tolist()
                out.append(d)
            return out

    def import_all(self, project: str, items: List[Dict]) -> int:
        count = 0
        for item in items:
            try:
                self.store(
                    content=item.get("content", ""),
                    project=project,
                    user_id=item.get("user_id"),
                    tags=item.get("tags"),
                    importance=item.get("importance", 1.0),
                    memory_type=item.get("memory_type", "semantic"),
                    pinned=bool(item.get("pinned", False)),
                    label=item.get("label"),
                    embedding=item.get("embedding"),
                )
                count += 1
            except Exception as e:
                logger.warning(f"[NSN] Skipped import item: {e}")
        return count

    # ── consolidation (called by sleep engine) ─────────────────────────────────

    def run_consolidation(self, project: Optional[str] = None) -> Dict[str, Any]:
        stats = {"boosted": 0, "decayed": 0, "archived": 0, "deduped": 0, "promoted": 0}
        proj_clause = "AND project=?" if project else ""
        proj_params = [project] if project else []

        with self._conn() as c:
            cur = c.cursor()

            # 1. Boost high-access memories
            cur.execute(f"""
                UPDATE memories
                SET consolidation_score = MIN(1.0, consolidation_score + (access_count * 0.08)),
                    access_count = 0,
                    last_consolidated_at = strftime('%Y-%m-%d %H:%M:%S','now')
                WHERE status='active' AND pinned=0 AND access_count > 0 {proj_clause}
            """, proj_params)
            stats["boosted"] = cur.rowcount

            # 2. Decay stale (no access for 7+ days)
            cur.execute(f"""
                UPDATE memories
                SET consolidation_score = MAX(0.0, consolidation_score * 0.95)
                WHERE status='active' AND pinned=0
                AND last_accessed_at < strftime('%Y-%m-%d %H:%M:%S','now','-7 days') {proj_clause}
            """, proj_params)
            stats["decayed"] = cur.rowcount

            # 3. Archive below survival threshold
            cur.execute(f"""
                UPDATE memories SET status='archived'
                WHERE status='active' AND pinned=0 AND consolidation_score < 0.15 {proj_clause}
            """, proj_params)
            stats["archived"] = cur.rowcount

            # 4. Episodic → Semantic promotion
            # A memory is promoted when consolidation_score >= 0.75 (encoded 3+ accesses + boosts).
            # On promotion: re-type to 'semantic', bump importance, mark label as [consolidated].
            # This makes promoted memories surface with higher confidence than fresh episodics.
            cur.execute(f"""
                UPDATE memories
                SET memory_type = 'semantic',
                    importance = MIN(1.0, importance + 0.15),
                    label = CASE WHEN label IS NULL THEN '[consolidated]'
                                 WHEN label NOT LIKE '%[consolidated]%' THEN label || ' [consolidated]'
                                 ELSE label END,
                    last_consolidated_at = strftime('%Y-%m-%d %H:%M:%S','now')
                WHERE status='active' AND memory_type='episodic'
                AND consolidation_score >= 0.75 {proj_clause}
            """, proj_params)
            stats["promoted"] = cur.rowcount

            # 5. Deduplication — cosine > 0.87 (tuned for real agent conversations)
            # 0.92 was too tight; near-duplicates at 0.85-0.91 should still merge
            rows = cur.execute(f"""
                SELECT id, embedding, consolidation_score FROM memories
                WHERE status='active' AND pinned=0 AND embedding IS NOT NULL {proj_clause}
            """, proj_params).fetchall()

            archived_ids = set()
            row_list = [(r["id"], np.frombuffer(r["embedding"], dtype=np.float32), r["consolidation_score"]) for r in rows]

            for i in range(len(row_list)):
                if row_list[i][0] in archived_ids: continue
                ei = row_list[i][1]
                ni = np.linalg.norm(ei)
                if ni == 0: continue
                ei_norm = ei / ni
                for j in range(i + 1, len(row_list)):
                    if row_list[j][0] in archived_ids: continue
                    ej = row_list[j][1]
                    nj = np.linalg.norm(ej)
                    if nj == 0: continue
                    sim = float(np.dot(ei_norm, ej / nj))
                    if sim > 0.87:
                        # Archive the one with lower consolidation score
                        keep_idx, drop_idx = (i, j) if row_list[i][2] >= row_list[j][2] else (j, i)
                        drop_id = row_list[drop_idx][0]
                        archived_ids.add(drop_id)
                        cur.execute("UPDATE memories SET status='archived' WHERE id=?", (drop_id,))
                        stats["deduped"] += 1

            # Log sleep cycle
            cur.execute("""
                INSERT INTO sleep_log (id, project, boosted, decayed, archived, deduped, promoted, started_at, finished_at)
                VALUES (?,?,?,?,?,?,?,strftime('%Y-%m-%d %H:%M:%S','now'),strftime('%Y-%m-%d %H:%M:%S','now'))
            """, (str(uuid.uuid4()), project or "all", stats["boosted"], stats["decayed"],
                  stats["archived"], stats["deduped"], stats["promoted"]))
            c.commit()

        return stats

    def get_sleep_log(self, project: str, limit: int = 10) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM sleep_log WHERE project=? ORDER BY finished_at DESC LIMIT ?",
                (project, limit)
            ).fetchall()
            return [dict(r) for r in rows]
