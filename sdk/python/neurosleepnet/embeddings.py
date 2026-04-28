"""
Local embedding manager for NeuroSleepNet.
Supports lazy loading of fastembed for zero-configuration local usage.
"""
import logging
from typing import List, Optional

logger = logging.getLogger("neurosleepnet.embeddings")

class EmbeddingManager:
    def __init__(self, provider: str = "local", model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        
        if self.provider == "local":
            self.model_name = model_name or "BAAI/bge-small-en-v1.5"
        elif self.provider == "openai":
            self.model_name = model_name or "text-embedding-3-small"
        else:
            self.model_name = model_name
            
        self._model = None
        self._openai_client = None

    def _load_model(self):
        if self._model is not None or self._openai_client is not None:
            return

        if self.provider == "local":
            try:
                from fastembed import TextEmbedding
                logger.info(f"[NSN] Loading local embedding model: {self.model_name}...")
                self._model = TextEmbedding(model_name=self.model_name)
            except ImportError:
                raise ImportError(
                    "fastembed is required for local embeddings. "
                    "Install with: pip install neurosleepnet[local] or pip install fastembed"
                )
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai is required for OpenAI embeddings. "
                    "Install with: pip install neurosleepnet[openai] or pip install openai"
                )
        elif self.provider == "none":
            pass # No embeddings
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        if self.provider == "none":
            return [[] for _ in texts]
            
        self._load_model()
        
        if self.provider == "local":
            # fastembed returns an iterator of numpy arrays
            embeddings = list(self._model.embed(texts))
            return [emb.tolist() for emb in embeddings]
            
        elif self.provider == "openai":
            response = self._openai_client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return [item.embedding for item in response.data]
            
        return []

    def embed_single(self, text: str) -> List[float]:
        if not text.strip():
            return []
        res = self.embed([text])
        return res[0] if res else []
