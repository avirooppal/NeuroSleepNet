import numpy as np
from typing import Any, Callable, Optional, Dict

class NSNLayer:
    """
    NeuroSleepNet Layer V2
    Includes Memory Edge Caching, Hybrid Retrieval, and Knowledge Graph extraction.
    """
    def __init__(self, model: Any, task_boundary: str = "manual", mode: str = "native"):
        self.model = model
        self.task_boundary = task_boundary
        self.mode = mode
        
        from .buffer import ReplayBuffer
        from .sleep import SleepScheduler
        from .attention import TaskAttention
        from .residual import ResidualPathway
        from .graph import KnowledgeGraphMemory
        
        self.buffer = ReplayBuffer()
        self.sleep_scheduler = SleepScheduler()
        self.attention = TaskAttention()
        self.residual = ResidualPathway()
        self.graph_memory = KnowledgeGraphMemory()
        
        self.last_embedding_mean = None
        self.current_auto_task_id = "task_0"
        self.auto_task_counter = 0

    def get_embedding(self, input_data: Any) -> np.ndarray:
        if isinstance(input_data, str):
            return np.array([float(ord(c)) for c in input_data[:128].ljust(128, ' ')]) / 255.0
        return np.random.rand(128)

    def detect_task_boundary(self, embedding: np.ndarray) -> str:
        if self.task_boundary == "manual":
            return self.current_auto_task_id
            
        cur_mean = np.mean(embedding)
        if self.last_embedding_mean is not None:
            shift = abs(cur_mean - self.last_embedding_mean)
            if shift > 0.3:
                self.auto_task_counter += 1
                self.current_auto_task_id = f"task_{self.auto_task_counter}"
                print(f"🔄 [NeuroSleepNet] Auto-detected task boundary shift. Now on {self.current_auto_task_id}")
                
        self.last_embedding_mean = cur_mean
        return self.current_auto_task_id

    def _inject_sidecar_prompt(self, input_data: str, task_id: str) -> str:
        """
        V2 Sidecar Mode: 
        1. Queries Knowledge Graph for entity relationships.
        2. Uses Hybrid Search for top latent memories.
        """
        q_emb = self.get_embedding(input_data)
        
        # 1. Edge-Optimized Hybrid Search (Increased top_k from 3 to 5)
        memories = self.buffer.sample(5, query=input_data, query_emb=q_emb, strategy="hybrid")
        
        # 2. Extract Graph Context
        graph_ctx = self.graph_memory.get_context(input_data)
        
        if not memories and not graph_ctx:
            return input_data
            
        context_str = ""
        if graph_ctx:
            context_str += f"- Graph Relations: {graph_ctx}\n"
            
        if memories:
            mem_str = "\n".join([f"- {m.get('input_data', '').strip()}" for m in memories])
            context_str += f"{mem_str}"
            
        prefix = f"Background Information:\n{context_str}\n\nQuery: "
        return prefix + input_data

    def learn(self, task_id: str, input_data: Any, label: Any = None, **kwargs):
        embedding = self.get_embedding(input_data)
        
        if self.task_boundary == "auto":
            task_id = self.detect_task_boundary(embedding)
            
        # Store in buffer (edge-cached)
        raw_text = input_data if isinstance(input_data, str) else str(label)
        self.buffer.store(task_id, embedding, label, raw_text=raw_text)
        
        # Store in graph memory
        if isinstance(input_data, str):
            self.graph_memory.add_memory(input_data)
        
        if self.sleep_scheduler.should_sleep(0, task_id):
            self.sleep()
            
        return {"status": "learned", "task_id": task_id}
        
    def predict(self, input_data: Any, task_id: str = "default", **kwargs):
        if self.mode == "sidecar" and isinstance(input_data, str):
            input_data = self._inject_sidecar_prompt(input_data, task_id)
            
        if callable(self.model):
            return self.model(input_data, **kwargs)
        elif hasattr(self.model, "predict"):
            return self.model.predict(input_data, **kwargs)
        elif hasattr(self.model, "__call__"):
            return self.model(input_data, **kwargs)
        else:
            raise ValueError("Wrapped model must be callable or have a .predict() method")
            
    def sleep(self):
        return self.sleep_scheduler.run_sleep(self.model, self.buffer)

def wrap(model: Any, task_boundary: str = "manual", mode: str = "native") -> NSNLayer:
    return NSNLayer(model, task_boundary=task_boundary, mode=mode)
