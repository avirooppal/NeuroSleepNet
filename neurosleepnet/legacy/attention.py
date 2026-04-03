import numpy as np

class TaskAttention:
    """
    Task-Aware Attention Module.
    """
    def __init__(self, embed_dim: int = 128):
        self.embed_dim = embed_dim
        # Mocking an embedding table with a dictionary
        self.task_embeddings = {}

    def encode_task(self, task_id: str) -> np.ndarray:
        if task_id not in self.task_embeddings:
            # Initialize with random normally distributed values
            self.task_embeddings[task_id] = np.random.randn(self.embed_dim)
        return self.task_embeddings[task_id]

    def gate(self, embedding: np.ndarray, task_ctx: np.ndarray) -> np.ndarray:
        # Sigmoid gate simulation
        gate_value = 1 / (1 + np.exp(-task_ctx))
        
        if embedding.shape[-1] <= gate_value.shape[-1]:
            gated = embedding * gate_value[:embedding.shape[-1]]
            return gated
        return embedding
