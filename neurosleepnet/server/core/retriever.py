import numpy as np
from typing import List, Dict, Any
from .graph_store import GraphStore
from ..models.memory_node import MemoryNode
from .ingestion import IngestionEngine

class Retriever:
    def __init__(self, store: GraphStore, ingestion: IngestionEngine):
        self.store = store
        self.ingestion = ingestion

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        v1, v2 = np.array(a), np.array(b)
        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            return 0.0
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def retrieve(self, user_id: str, query: str, task_id: str, top_k: int = 5) -> str:
        q_emb = self.ingestion._get_embedding(query)
        nodes = self.store.get_nodes(user_id=user_id, task_id=None) # Fetch all active nodes for user
        
        scored_nodes = []
        for node in nodes:
            if not node.embedding:
                continue
            
            # Score = α·cosine_sim + β·task_match + γ·recency (simplified)
            sim = self._cosine_similarity(q_emb, node.embedding)
            task_bonus = 0.2 if node.task_id == task_id else 0.0
            
            # Total score
            score = sim + task_bonus
            scored_nodes.append((score, node))
            
        # Sort desc
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        top_nodes = [n for score, n in scored_nodes[:top_k]]
        
        if not top_nodes:
            return ""
            
        context_lines = [f"- {n.content}" for n in top_nodes]
        return "\n".join(context_lines)
