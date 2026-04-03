import os
import uuid
import numpy as np
from typing import List, Dict, Any
from ..models.memory_node import MemoryNode
from .graph_store import GraphStore

class IngestionEngine:
    def __init__(self, store: GraphStore):
        self.store = store
        self.use_openai = bool(os.getenv("OPENAI_API_KEY"))
        if self.use_openai:
            from openai import OpenAI
            self.client = OpenAI()

    def _get_embedding(self, text: str) -> List[float]:
        if self.use_openai:
            resp = self.client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding
        # Fallback pseudo-embedding dictating consistent vector per text
        np.random.seed(sum(ord(c) for c in text[:50]))
        return np.random.rand(1536).tolist()

    def process_messages(self, user_id: str, session_id: str, task_id: str, messages: List[Dict[str, str]]):
        """
        Takes raw chat messages, extracts facts, embeds them, and stores them.
        In a real app, you'd use an LLM extraction prompt here. For MVP, we chunk.
        """
        for msg in messages:
            if msg.get("role") != "user":
                continue # Only extract facts from user
                
            content = msg.get("content", "")
            if not content:
                continue

            # MVP Chunking: Treat the message as a top-level fact
            embedding = self._get_embedding(content)
            
            node = MemoryNode(
                user_id=user_id,
                task_id=task_id,
                session_id=session_id,
                content=content,
                type="fact",
                embedding=embedding,
                metadata={"source": "ingestion"}
            )
            self.store.write_node(node)
