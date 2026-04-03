import sqlite3
import json
from ..models.memory_node import MemoryNode
from typing import List, Optional

class GraphStore:
    def __init__(self, db_path: str = "neurosleep_memory.db"):
        self.db_path = db_path
        self._init_db()
        
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
        
    def _init_db(self):
        with self._get_conn() as conn:
            # Main nodes table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    task_id TEXT,
                    session_id TEXT,
                    content TEXT,
                    type TEXT,
                    embedding_json TEXT,
                    superseded INTEGER,
                    confidence REAL,
                    weight REAL,
                    created_at TEXT,
                    metadata_json TEXT
                )
            ''')
            # Edges table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memory_edges (
                    source_id TEXT,
                    target_id TEXT,
                    relation TEXT,
                    FOREIGN KEY(source_id) REFERENCES memory_nodes(id),
                    FOREIGN KEY(target_id) REFERENCES memory_nodes(id)
                )
            ''')
            # Indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_task ON memory_nodes (user_id, task_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_superseded ON memory_nodes (superseded)')
            
    def write_node(self, node: MemoryNode):
        with self._get_conn() as conn:
            conn.execute('''
                INSERT INTO memory_nodes 
                (id, user_id, task_id, session_id, content, type, embedding_json, superseded, confidence, weight, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node.id, node.user_id, node.task_id, node.session_id, node.content, 
                node.type, json.dumps(node.embedding) if node.embedding else None,
                int(node.superseded), node.confidence, node.weight, 
                node.created_at.isoformat(), json.dumps(node.metadata)
            ))

    def write_edge(self, source_id: str, target_id: str, relation: str):
        with self._get_conn() as conn:
            conn.execute('INSERT INTO memory_edges (source_id, target_id, relation) VALUES (?, ?, ?)',
                         (source_id, target_id, relation))
                         
    def get_nodes(self, user_id: str, task_id: Optional[str] = None, include_superseded: bool = False) -> List[MemoryNode]:
        query = "SELECT * FROM memory_nodes WHERE user_id = ?"
        params = [user_id]
        
        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
            
        if not include_superseded:
            query += " AND superseded = 0"
            
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            
        result = []
        for r in rows:
            node = MemoryNode(
                id=r['id'],
                user_id=r['user_id'],
                task_id=r['task_id'],
                session_id=r['session_id'],
                content=r['content'],
                type=r['type'],
                embedding=json.loads(r['embedding_json']) if r['embedding_json'] else None,
                superseded=bool(r['superseded']),
                confidence=r['confidence'],
                weight=r['weight'],
                created_at=r['created_at'],
                metadata=json.loads(r['metadata_json'])
            )
            result.append(node)
        return result
        
    def mark_superseded(self, node_id: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE memory_nodes SET superseded = 1 WHERE id = ?", (node_id,))
