import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Any

class OfflineCache:
    def __init__(self, db_path: str = None):
        if db_path is None:
            home = str(Path.home())
            cache_dir = os.path.join(home, ".nsn")
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            self.db_path = os.path.join(cache_dir, "cache.db")
        else:
            self.db_path = db_path
            
        self._init_db()

    def _init_db(self):
        import contextlib
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Check current version
            cursor.execute("PRAGMA user_version;")
            version = cursor.fetchone()[0]
            
            if version == 0:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        tags TEXT,
                        importance REAL,
                        project TEXT,
                        session_id TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("PRAGMA user_version = 1;")
                version = 1
                
            if version == 1:
                # Add schema_version column and other new columns if any
                try:
                    cursor.execute("ALTER TABLE memories_cache ADD COLUMN schema_version INTEGER DEFAULT 2")
                except sqlite3.OperationalError:
                    pass # Column exists
                cursor.execute("PRAGMA user_version = 2;")
                version = 2
                
            conn.commit()

    def store(self, content: str, project: str, session_id: str, tags: list = None, importance: float = 1.0):
        import contextlib
        tags_str = json.dumps(tags) if tags else "[]"
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories_cache (content, tags, importance, project, session_id)
                VALUES (?, ?, ?, ?, ?)
            """, (content, tags_str, importance, project, session_id))
            conn.commit()

    def retrieve(self, project: str, limit: int = 5) -> List[Dict[str, Any]]:
        import contextlib
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, tags, importance, session_id, timestamp
                FROM memories_cache
                WHERE project = ?
                ORDER BY id DESC
                LIMIT ?
            """, (project, limit))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
