from typing import List, Dict
import numpy as np
from .graph_store import GraphStore
from ..models.memory_node import MemoryNode

class ConsolidationEngine:
    """Sleep replay engine: Deduplicates, merges, and decays memories async."""
    def __init__(self, store: GraphStore):
        self.store = store

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        v1, v2 = np.array(a), np.array(b)
        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            return 0.0
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def run_consolidation(self, user_id: str):
        """
        Merge duplicates. (O(n^2) naive approach for MVP).
        """
        nodes = self.store.get_nodes(user_id=user_id)
        if not nodes:
            return
            
        superseded_ids = set()
        
        # 1. Merge near-duplicates
        nodes_to_check = [n for n in nodes if n.id not in superseded_ids and n.embedding]
        for i in range(len(nodes_to_check)):
            n1 = nodes_to_check[i]
            if n1.id in superseded_ids: continue
                
            for j in range(i+1, len(nodes_to_check)):
                n2 = nodes_to_check[j]
                if n2.id in superseded_ids: continue
                    
                sim = self._cosine_similarity(n1.embedding, n2.embedding)
                if sim > 0.92:
                    # Near duplicate detected
                    to_keep, to_drop = (n1, n2) if n1.created_at >= n2.created_at else (n2, n1)
                    
                    self.store.mark_superseded(to_drop.id)
                    superseded_ids.add(to_drop.id)
                    self.store.write_edge(to_keep.id, to_drop.id, "supersedes")

        # Additional steps like Contradiction Handling and Decay would run here.
