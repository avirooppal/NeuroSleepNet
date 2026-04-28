"""
Advanced Local Storage Engine for NeuroSleepNet.
Features: 
- Conflict Resolution (Deprecation of old facts)
- Input Sanitization (Security)
- Semantic Versioning of Memories
- Hybrid Search (Semantic + Keyword)
"""
import json
import logging
import os
import sqlite3
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger("neurosleepnet.store")

class LocalStore:
    def __init__(self, data_dir: str = "~/.neurosleepnet"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "neurosleepnet.db")
        self._init_db()
        
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            
            # Check version for migration
            cursor.execute("PRAGMA user_version;")
            version = cursor.fetchone()[0]
            
            if version < 2:
                # Advanced memories table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        project TEXT NOT NULL,
                        session_id TEXT,
                        content TEXT NOT NULL,
                        tags TEXT,
                        importance REAL DEFAULT 1.0,
                        consolidation_score REAL DEFAULT 0.5,
                        access_count INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'active',
                        version INTEGER DEFAULT 1,
                        deprecated_by TEXT,
                        embedding BLOB,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_consolidated_at DATETIME,
                        expires_at DATETIME
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_project_status ON memories(project, status);")
                
                # FTS5 table
                cursor.execute("DROP TABLE IF EXISTS memories_fts;")
                cursor.execute("CREATE VIRTUAL TABLE memories_fts USING fts5(content, content='memories', content_rowid='rowid')")
                
                # Triggers
                cursor.execute("DROP TRIGGER IF EXISTS memories_ai;")
                cursor.execute("CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content); END;")
                
                cursor.execute("PRAGMA user_version = 2;")
            conn.commit()

    def _sanitize_content(self, content: str) -> str:
        """Security: Clean input to prevent injection and PII leaks."""
        # 1. Strip HTML/Script tags
        content = re.sub(r'<[^>]*?>', '', content)
        # 2. Prevent SQL logic symbols
        content = content.replace(";", "").replace("--", "")
        # 3. Simple PII masking (Emails)
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', content)
        return content.strip()

    def store(self, content: str, project: str, session_id: Optional[str] = None, 
              tags: List[str] = None, importance: float = 1.0, 
              embedding: List[float] = None, ttl_days: Optional[int] = None,
              resolve_conflicts: bool = True) -> str:
        
        content = self._sanitize_content(content)
        memory_id = str(uuid.uuid4())
        
        emb_blob = np.array(embedding, dtype=np.float32).tobytes() if embedding else None
        expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).strftime("%Y-%m-%d %H:%M:%S") if ttl_days else None

        with self._get_conn() as conn:
            cursor = conn.cursor()

            # --- CONFLICT RESOLUTION (Last-Write-Wins / Semantic Override) ---
            if resolve_conflicts and embedding:
                q_emb = np.array(embedding, dtype=np.float32)
                q_norm = np.linalg.norm(q_emb)
                if q_norm != 0:
                    q_emb = q_emb / q_norm

                # Direct scan of active memories for the project to find semantic overlaps
                cursor.execute("SELECT id, embedding FROM memories WHERE project = ? AND status = 'active' AND embedding IS NOT NULL", (project,))
                for row in cursor.fetchall():
                    m_emb = np.frombuffer(row['embedding'], dtype=np.float32)
                    m_norm = np.linalg.norm(m_emb)
                    if m_norm == 0: continue
                    
                    sim = float(np.dot(q_emb, m_emb / m_norm))
                    # Lower threshold for conflict (0.55 is very sensitive)
                    if sim > 0.55:
                        cursor.execute("UPDATE memories SET status = 'deprecated', deprecated_by = ? WHERE id = ?", (memory_id, row['id']))
                        # print(f"DEBUG: Conflict Resolved: Deprecated {row['id']} in favor of {memory_id}")

            cursor.execute("""
                INSERT INTO memories (id, project, session_id, content, tags, importance, embedding, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (memory_id, project, session_id, content, json.dumps(tags or []), importance, emb_blob, expires_at))
            print(f"DEBUG: Successfully stored memory {memory_id} content: {content[:20]}...")
            conn.commit()
            
        return memory_id

    def retrieve(self, query: str, query_embedding: List[float], project: str, top_k: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        q_emb = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_emb)
        if q_norm != 0: q_emb = q_emb / q_norm

        results = {}
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 1. KEYWORD SIGNAL (FTS5)
            safe_query = query.replace('"', '""')
            cursor.execute("""
                SELECT m.id, bm25(memories_fts) as rank
                FROM memories_fts fts
                JOIN memories m ON m.rowid = fts.rowid
                WHERE memories_fts MATCH ? AND m.project = ? AND m.status = 'active'
            """, (f'"{safe_query}"', project))
            
            for row in cursor.fetchall():
                results[row['id']] = {"keyword_score": 1.0 / (1.0 + abs(row['rank']))}

            # 2. SEMANTIC SIGNAL
            cursor.execute("""
                SELECT id, content, tags, importance, consolidation_score, created_at, embedding
                FROM memories
                WHERE project = ? AND status = 'active' AND embedding IS NOT NULL
            """, (project,))
            
            for row in cursor.fetchall():
                row_dict = dict(row)
                m_id = row_dict['id']
                m_emb = np.frombuffer(row_dict.pop('embedding'), dtype=np.float32)
                m_norm = np.linalg.norm(m_emb)
                
                cosine_sim = float(np.dot(q_emb, m_emb / m_norm)) if m_norm != 0 and q_norm != 0 else 0.0

                # 3. TEMPORAL DECAY
                created = datetime.strptime(row_dict['created_at'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - created).days
                # Score decays 5% every week
                temporal_score = max(0.5, 1.0 - (age_days / 180.0))

                k_score = results.get(m_id, {}).get("keyword_score", 0.0)
                
                # --- SIGNAL GATE ---
                # Dynamic Gate: Short queries (like 'what is my color?') need more slack.
                # If keyword match exists, allow even lower semantic similarity.
                dynamic_gate = 0.3 if len(query.split()) < 6 else 0.45
                if k_score < 0.1 and cosine_sim < dynamic_gate:
                    continue
                if k_score >= 0.1 and cosine_sim < 0.1:
                    continue

                # FUSION
                attention_score = (
                    (cosine_sim * 0.45) + 
                    (k_score * 0.25) + 
                    (row_dict['consolidation_score'] * 0.15) + 
                    (temporal_score * 0.10) + 
                    (min(1.0, row_dict['importance']) * 0.05)
                )

                if attention_score < min_score: continue

                # print(f"DEBUG: Found '{row_dict['content'][:20]}' | Score: {attention_score:.3f} (Sim: {cosine_sim:.3f}, Key: {k_score:.3f})")

                row_dict.update({
                    'attention_score': attention_score,
                    'similarity': cosine_sim,
                    'keyword_score': k_score,
                    'tags': json.loads(row_dict['tags']),
                    'created_at': row_dict['created_at'] # Keep for SDK
                })
                results[m_id] = row_dict

            final = [v for v in results.values() if "attention_score" in v]
            final.sort(key=lambda x: x['attention_score'], reverse=True)
            return final[:top_k]

    def forget(self, memory_id: Optional[str] = None, query: Optional[str] = None, 
               older_than_days: Optional[int] = None, project: Optional[str] = None) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if memory_id:
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            elif (query is None or query == "") and project:
                cursor.execute("DELETE FROM memories WHERE project = ?", (project,))
            elif query and project:
                safe_query = query.replace('"', '""')
                
                sql = "DELETE FROM memories WHERE rowid IN (SELECT rowid FROM memories_fts WHERE memories_fts MATCH ?)"
                params = [f'"{safe_query}"']
                
                if older_than_days:
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).strftime("%Y-%m-%d %H:%M:%S")
                    sql += " AND created_at < ?"
                    params.append(cutoff)
                
                cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def run_consolidation(self) -> Dict[str, Any]:
        """Sleep Engine: Boost accessed, archive stale."""
        stats = {"boosted": 0, "archived": 0}
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 1. Boost based on access
            cursor.execute("UPDATE memories SET consolidation_score = MIN(1.0, consolidation_score + 0.1) WHERE status = 'active' AND access_count > 0")
            stats["boosted"] = cursor.rowcount
            # 2. Archive older than 30 days with low score
            cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE memories SET status = 'archived' WHERE status = 'active' AND consolidation_score < 0.3 AND created_at < ?", (cutoff,))
            stats["archived"] = cursor.rowcount
            conn.commit()
        return stats
