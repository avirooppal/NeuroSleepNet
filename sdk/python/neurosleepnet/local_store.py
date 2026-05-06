"""
LocalStore — SQLite-backed persistent memory for NeuroSleepNet (Import Mode).
"""
import json, logging, os, re, sqlite3, uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
from .embeddings import EmbeddingCache

logger = logging.getLogger("neurosleepnet.store")


class LocalStore:
    def __init__(self, data_dir: str = "~/.neurosleepnet"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "neurosleepnet.db")
        # Per-project ANN caches — populated lazily on first retrieve() call
        self._caches: Dict[str, EmbeddingCache] = {}
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
                    settings TEXT DEFAULT '{}',
                    last_sleep_at TEXT
                );

                CREATE TABLE IF NOT EXISTS links (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT DEFAULT 'related',
                    weight REAL DEFAULT 1.0,
                    PRIMARY KEY (source_id, target_id),
                    FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE
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
        self._add_column_if_missing("project_meta", "last_sleep_at", "TEXT")

        # Post-migration indices
        with self._conn() as c:
            c.execute("CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(project, user_id, status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_mem_proj ON memories(project, status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_mem_pinned ON memories(project, pinned, status)")
            c.commit()

    # ── helpers ────────────────────────────────────────────────────────────────

    def _get_cache(self, project: str) -> EmbeddingCache:
        """Return (and lazily warm) the per-project ANN cache."""
        if project not in self._caches:
            cache = EmbeddingCache()
            self._warm_cache(project, cache)
            self._caches[project] = cache
        return self._caches[project]

    def _warm_cache(self, project: str, cache: EmbeddingCache):
        """Populate cache from existing DB rows on first access."""
        try:
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id, embedding FROM memories "
                    "WHERE project=? AND status='active' AND embedding IS NOT NULL",
                    (project,)
                ).fetchall()
            blob_rows = [(r["id"], bytes(r["embedding"])) for r in rows]
            if blob_rows:
                cache.rebuild(blob_rows)
                logger.debug(f"[NSN Cache] Warmed project '{project}' with {len(blob_rows)} embeddings")
        except Exception as e:
            logger.warning(f"[NSN Cache] Warm failed for '{project}': {e}")

    def _get_embedding_blob(self, memory_id: str) -> Optional[bytes]:
        """Fetch raw embedding blob for a single memory (used by synthesis clustering)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT embedding FROM memories WHERE id=?", (memory_id,)
            ).fetchone()
        return bytes(row["embedding"]) if row and row["embedding"] else None

    def _access_velocity(self, access_count: int, created_at_str: str) -> float:
        """
        P1-7: Log-normalized access velocity signal.
        raw_velocity = access_count / days_since_created (min 1 minute)
        normalized   = log(1 + raw_velocity) / log(1 + 100)  -> [0, 1]
        max weight contribution: 0.04 (tiebreaker only, never primary signal)
        """
        try:
            created = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            days = max(1 / 1440, (datetime.now(timezone.utc) - created).total_seconds() / 86400)
            raw_velocity = access_count / days
            import math
            return min(1.0, math.log(1 + raw_velocity) / math.log(1 + 100))
        except Exception:
            return 0.0

    def _expand_graph(
        self,
        cur,
        top_ids: List[str],
        all_scores: Dict[str, float],
        max_additional: int = 10,
        max_hops: int = 2,
    ) -> Dict[str, float]:
        """
        P1-6: BFS graph expansion — surfaces memories linked via the `links` table.
        Capped at max_hops=2 and max_additional=10 to prevent unbounded fetches.
        Linked memories receive a discounted score: parent_score * weight * 0.7^hop.
        """
        expanded: Dict[str, float] = {}
        frontier = set(top_ids)
        visited = set(top_ids)

        for hop in range(max_hops):
            if len(expanded) >= max_additional or not frontier:
                break
            placeholders = ",".join("?" * len(frontier))
            frontier_list = list(frontier)
            try:
                rows = cur.execute(
                    f"SELECT source_id, target_id, weight FROM links "
                    f"WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
                    frontier_list * 2,
                ).fetchall()
            except Exception:
                break

            next_frontier: set = set()
            for row in rows:
                row_dict = dict(row)  # sqlite3.Row has no .get() — convert first
                src, tgt = row_dict["source_id"], row_dict["target_id"]
                w = row_dict.get("weight", 0.5)
                neighbor = tgt if src in frontier else src
                if neighbor in visited:
                    continue
                parent_score = max((all_scores.get(sid, 0.0) for sid in frontier), default=0.0)
                expanded[neighbor] = parent_score * w * (0.7 ** hop)
                visited.add(neighbor)
                next_frontier.add(neighbor)
                if len(expanded) >= max_additional:
                    break
            frontier = next_frontier

        return expanded

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

        # Update ANN cache incrementally (if cache already warmed for this project)
        if embedding and project in self._caches:
            self._caches[project].add(mid, embedding)

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
        """Calculate the attention score based on hybrid weights."""
        w = weights
        base_score = (
            (similarity * w.get("w_sim", 0.45)) +
            (recency * w.get("w_rec", 0.15)) +
            (consolidation * w.get("w_con", 0.25)) +
            (feedback * w.get("w_fb", 0.15))
        )
        return base_score * importance

    def _apply_stage2_reranking(self, query: str, candidates: List[Dict], top_k: int) -> List[Dict]:
        """
        V2: Stage 2 Re-ranking (Cognitive Precision).

        Cross-score is a keyword-density refinement signal — it must boost
        semantically strong results, not override them. Formula (P0-2 fix):
          new_score = base * (1 + 0.20 * cross_score)  — only when base > 0.3
        This means a perfect semantic match (base=0.9) gets at most +18%,
        while a noise memory (base=0.1) is never promoted by keyword overlap.
        """
        if len(candidates) <= top_k:
            return candidates

        q_words = set(query.lower().split())
        for m in candidates:
            if m.get("pinned"):
                continue
            base = m["attention_score"]
            if base <= 0.3 or not q_words:
                # Below noise floor — cross-score cannot rescue it
                continue
            m_words = set(m.get("content", "").lower().split())
            overlap = q_words.intersection(m_words)
            cross_score = len(overlap) / len(q_words)
            # Refine only — cap at 1.0
            m["attention_score"] = min(1.0, base * (1.0 + 0.20 * cross_score))

        return sorted(
            candidates,
            key=lambda x: (x.get("pinned", False), x["attention_score"]),
            reverse=True
        )

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

            # Base filter clauses
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

            # 3a. Dense semantic signal via ANN cache (P0-1)
            #     Query the in-memory matrix — no full-table embedding scan.
            #     Then fetch only the candidate rows from DB by ID.
            if use_dense:
                cache = self._get_cache(project)
                ann_results = cache.query(query_embedding, top_k=top_k * 4)
                if ann_results:
                    candidate_ids = [r[0] for r in ann_results]
                    cosine_by_id = {r[0]: r[1] for r in ann_results}

                    # Filter by user and memory_type in one DB fetch
                    id_placeholders = ",".join("?" * len(candidate_ids))
                    sem_rows = cur.execute(f"""
                        SELECT id, content, tags, importance, consolidation_score,
                               feedback_score, memory_type, created_at, pinned, label
                        FROM memories
                        WHERE id IN ({id_placeholders})
                          AND project=? AND status='active'
                          {type_clause}{user_clause}
                    """, candidate_ids + [project] + type_params + user_params).fetchall()
                else:
                    sem_rows = []
                    cosine_by_id = {}
            else:
                # 3b. Sparse / TF-IDF path — existing behaviour (no embedding scan)
                sem_rows = cur.execute(f"""
                    SELECT id, content, tags, importance, consolidation_score,
                           feedback_score, memory_type, created_at, pinned, label
                    FROM memories
                    WHERE project=? AND status='active'
                    {type_clause}{user_clause}
                """, [project] + type_params + user_params).fetchall()
                cosine_by_id = {}

            for row in sem_rows:
                d = dict(row)
                mid = d["id"]
                if mid in results and results[mid].get("pinned"):
                    continue

                cosine = cosine_by_id.get(mid, 0.0)

                recency = self._normalize_recency(d["created_at"])
                k_score = results.get(mid, {}).get("keyword_score", 0.0)
                tfidf_score = tfidf_scores.get(mid, 0.0)
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

            # Apply V2 Cognitive Re-ranking (P0-2 fix applied)
            candidates = final[:max(top_k * 4, 20)]
            final = self._apply_stage2_reranking(query, candidates, top_k)

            # P1-6: Graph expansion — surface linked memories not in top candidates
            top_scores = {m["id"]: m["attention_score"] for m in final[:top_k]}
            if top_scores:
                graph_scores = self._expand_graph(cur, list(top_scores.keys()), top_scores)
                if graph_scores:
                    graph_ids = list(graph_scores.keys())
                    gid_placeholders = ",".join("?" * len(graph_ids))
                    g_rows = cur.execute(f"""
                        SELECT id, content, tags, importance, consolidation_score,
                               feedback_score, memory_type, created_at, pinned, label
                        FROM memories
                        WHERE id IN ({gid_placeholders})
                          AND project=? AND status='active'
                    """, graph_ids + [project]).fetchall()
                    for grow in g_rows:
                        gd = dict(grow)
                        gmid = gd["id"]
                        if gmid not in results:
                            gd.update({
                                "attention_score": round(graph_scores[gmid], 4),
                                "similarity": 0.0,
                                "keyword_score": 0.0,
                                "tags": json.loads(gd.get("tags") or "[]"),
                                "pinned": bool(gd.get("pinned", 0)),
                                "_graph_expanded": True,
                            })
                            final.append(gd)

                    # Re-sort after graph injection
                    final = sorted(
                        final,
                        key=lambda x: (x.get("pinned", False), x["attention_score"]),
                        reverse=True,
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

            # Update token_savings estimate
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

            # Read last_sleep_at for incremental dedup (P0-4)
            last_sleep_at = "1970-01-01 00:00:00"
            if project:
                row = cur.execute(
                    "SELECT last_sleep_at FROM project_meta WHERE project=?", (project,)
                ).fetchone()
                if row and row["last_sleep_at"]:
                    last_sleep_at = row["last_sleep_at"]

            # 1. Boost high-access memories (P1-8: diminishing returns)
            #    score += access_count * 0.08 / (1 + score)
            #    Prevents a burst of 10 accesses before first sleep from
            #    saturating the score in one cycle (old formula: +0.8 flat).
            cur.execute(f"""
                UPDATE memories
                SET consolidation_score = MIN(1.0,
                        consolidation_score +
                        (access_count * 0.08 / (1.0 + consolidation_score))
                    ),
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

            # 5. Incremental dedup (P0-4)
            #    Only compare memories added SINCE last sleep against the full corpus.
            #    This keeps dedup O(n·m) where m = new memories since last cycle.
            new_rows = cur.execute(f"""
                SELECT id, embedding, consolidation_score FROM memories
                WHERE status='active' AND pinned=0 AND embedding IS NOT NULL
                AND created_at >= ? {proj_clause}
            """, [last_sleep_at] + proj_params).fetchall()

            all_rows = cur.execute(f"""
                SELECT id, embedding, consolidation_score FROM memories
                WHERE status='active' AND pinned=0 AND embedding IS NOT NULL {proj_clause}
            """, proj_params).fetchall()

            all_vecs = [
                (r["id"], np.frombuffer(r["embedding"], dtype=np.float32), r["consolidation_score"])
                for r in all_rows
            ]
            archived_ids: set = set()

            for new_r in new_rows:
                nid = new_r["id"]
                if nid in archived_ids:
                    continue
                ne = np.frombuffer(new_r["embedding"], dtype=np.float32)
                nn = np.linalg.norm(ne)
                if nn == 0:
                    continue
                ne_norm = ne / nn
                n_score = new_r["consolidation_score"]

                for aid, ae, a_score in all_vecs:
                    if aid == nid or aid in archived_ids:
                        continue
                    an = np.linalg.norm(ae)
                    if an == 0:
                        continue
                    sim = float(np.dot(ne_norm, ae / an))
                    if sim > 0.87:
                        # Archive lower-scored duplicate
                        drop_id = nid if n_score < a_score else aid
                        archived_ids.add(drop_id)
                        cur.execute(
                            "UPDATE memories SET status='archived' WHERE id=?",
                            (drop_id,)
                        )
                        stats["deduped"] += 1

            # Log sleep cycle
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                INSERT INTO sleep_log (id, project, boosted, decayed, archived, deduped, promoted, started_at, finished_at)
                VALUES (?,?,?,?,?,?,?,strftime('%Y-%m-%d %H:%M:%S','now'),strftime('%Y-%m-%d %H:%M:%S','now'))
            """, (str(uuid.uuid4()), project or "all", stats["boosted"], stats["decayed"],
                  stats["archived"], stats["deduped"], stats["promoted"]))

            # Persist last_sleep_at so next cycle only dedupes new memories (P0-4)
            if project:
                cur.execute(
                    "UPDATE project_meta SET last_sleep_at=? WHERE project=?",
                    (now_str, project)
                )

            c.commit()

        # Invalidate ANN cache for this project so next recall() re-warms cleanly
        if project and project in self._caches:
            del self._caches[project]

        return stats

    def merge_memories(self, project: str, memory_ids: List[str],
                       synthesized_content: str) -> str:
        """
        V2 Synthesis: Merges episodic memories into one semantic master node.
        Archives originals, writes graph links, and seeds the master node with
        the cluster's avg consolidation_score so it surfaces in recall immediately
        (without waiting for the next sleep cycle).
        """
        # Read cluster stats BEFORE opening the write connection
        # (store() opens its own connection; nesting causes empty embeddings)
        with self._conn() as c:
            placeholders = ",".join("?" * len(memory_ids))
            src_rows = c.execute(
                f"SELECT consolidation_score, importance FROM memories WHERE id IN ({placeholders})",
                memory_ids
            ).fetchall()
        avg_consolidation = (
            sum(r["consolidation_score"] for r in src_rows) / max(1, len(src_rows))
        )
        max_importance = max((r["importance"] for r in src_rows), default=0.9)

        # 1. Compute embedding for the synthesized content so the master node
        #    is immediately queryable via ANN cache after cache invalidation.
        #    Use the global embed manager if available (import-mode); fall back
        #    to None (TF-IDF retrieval will still work).
        master_embedding = None
        try:
            from . import _ctx as _nsn_ctx
            if _nsn_ctx.embed is not None:
                master_embedding = _nsn_ctx.embed.embed_single(synthesized_content)
        except Exception:
            pass

        # Create the semantic master node
        mid = self.store(
            content=synthesized_content,
            project=project,
            memory_type="semantic",
            importance=min(1.0, max(0.9, max_importance)),
            label="[synthesized]",
            embedding=master_embedding,
        )

        # 2. Apply cluster consolidation boost + archive originals + write links
        with self._conn() as c:
            cur = c.cursor()

            # Seed master with cluster's avg so it ranks highly immediately
            cur.execute(
                "UPDATE memories SET consolidation_score=? WHERE id=?",
                (min(1.0, avg_consolidation + 0.1), mid)
            )

            for old_id in memory_ids:
                cur.execute(
                    "UPDATE memories SET status='archived', deprecated_by=? WHERE id=?",
                    (mid, old_id)
                )
                cur.execute(
                    "INSERT OR IGNORE INTO links (source_id, target_id, relation_type) "
                    "VALUES (?,?,?)",
                    (old_id, mid, "synthesized_into")
                )

            c.commit()

        # Invalidate ANN cache — master node must be visible on next recall()
        if project in self._caches:
            del self._caches[project]

        return mid


    def get_sleep_log(self, project: str, limit: int = 10) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM sleep_log WHERE project=? ORDER BY finished_at DESC LIMIT ?",
                (project, limit)
            ).fetchall()
            return [dict(r) for r in rows]
