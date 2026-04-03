import numpy as np
import json
import os
import time
from typing import List, Dict, Any
from .retrieval import HybridSearchEngine

class EdgeCache:
    """
    LRU Edge Cache to achieve sub-100ms queries without hitting remote DBs.
    """
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache = {}
        self.access_times = {}

    def get(self, key: str) -> Any:
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set(self, key: str, value: Any):
        if len(self.cache) >= self.capacity and key not in self.cache:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        self.cache[key] = value
        self.access_times[key] = time.time()
        
    def values(self) -> List[Any]:
        return list(self.cache.values())

class ReplayBuffer:
    """
    Latent Replay Buffer with Edge-Optimized Caching and Zero-Ops Local Support.
    """
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "local")
        self.use_local = (self.redis_url == "local")
        self.db_prefix = "nsn:memory:"
        
        # Edge cache for sub-100ms retrieval
        self.edge_cache = EdgeCache()
        
        # Zero-ops mock DB
        self.local_db = {}
        
        if not self.use_local:
            import redis
            try:
                self.redis = redis.from_url(self.redis_url)
                self.redis.ping()
            except Exception as e:
                print(f"⚠️ [NeuroSleepNet] Redis connection failed, falling back to local edge cache.")
                self.use_local = True

        self.hybrid_search = HybridSearchEngine(alpha=0.6)

    def store(self, task_id: str, embedding: np.ndarray, label: Any = None, raw_text: str = ""):
        """
        Store a new memory.
        """
        score = self.score(embedding)
        import uuid
        memory_id = f"{self.db_prefix}{task_id}:{uuid.uuid4().hex[:8]}"
        
        data = {
            "id": memory_id,
            "task_id": task_id,
            "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
            "label": label,
            "input_data": raw_text,
            "score": score,
            "timestamp": time.time()
        }
        
        # Update edge cache instantly (Incremental Indexing)
        self.edge_cache.set(memory_id, data)
        self.local_db[memory_id] = data
        
        if not self.use_local:
            try:
                self.redis.set(memory_id, json.dumps(data))
                self.redis.zadd(f"{self.db_prefix}zset", {memory_id: score})
            except Exception:
                self.use_local = True # Fallback if Redis fails mid-flight

    def sample(self, n: int, query: str = "", query_emb: np.ndarray = None, strategy: str = "hybrid") -> List[Dict[str, Any]]:
        """
        Sample n memories.
        strategy="hybrid" uses the Hybrid Semantic + Keyword Search over the edge cache.
        """
        all_memories = self.edge_cache.values()
        
        if strategy == "hybrid" and query and query_emb is not None:
            # Sub-100ms search over local edge cache
            return self.hybrid_search.search(query, query_emb, all_memories, top_k=n)
            
        # Fallback to simple subset
        return all_memories[:n]

    def score(self, embedding: np.ndarray) -> float:
        """ Calculate novelty score. """
        try:
            return float(np.var(embedding) + np.random.rand() * 0.1)
        except Exception:
            return 0.5
