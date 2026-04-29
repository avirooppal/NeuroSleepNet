"""
embed.py — Embedding manager with full fallback chain for NeuroSleepNet.

Fallback order: local (fastembed) → openai → cohere → tfidf

TF-IDF fallback guarantees recall always returns results even with zero
embedding infrastructure. Quality degrades gracefully, not catastrophically.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("neurosleepnet.embed")

# ── TF-IDF implementation (zero-dependency) ────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-z]{2,}\b", text.lower())


class TFIDFIndex:
    """
    Minimal in-process TF-IDF engine.
    Maintains a corpus of documents and produces cosine-similar sparse vectors.
    Not persisted — rebuilt on each process start from stored memory content.
    """
    def __init__(self):
        self._corpus: List[List[str]] = []   # tokenized docs
        self._ids: List[str] = []            # parallel doc IDs
        self._idf: Dict[str, float] = {}
        self._dirty = True

    def add(self, doc_id: str, text: str):
        tokens = _tokenize(text)
        self._corpus.append(tokens)
        self._ids.append(doc_id)
        self._dirty = True

    def _build_idf(self):
        N = len(self._corpus)
        if N == 0:
            self._idf = {}
            self._dirty = False
            return
        df: Counter = Counter()
        for tokens in self._corpus:
            for t in set(tokens):
                df[t] += 1
        self._idf = {t: math.log((N + 1) / (cnt + 1)) + 1 for t, cnt in df.items()}
        self._dirty = False

    def _tfidf_vec(self, tokens: List[str]) -> Dict[str, float]:
        if self._dirty:
            self._build_idf()
        tf: Counter = Counter(tokens)
        total = len(tokens) or 1
        vec: Dict[str, float] = {}
        for t, cnt in tf.items():
            idf = self._idf.get(t, 0.0)
            if idf > 0:
                vec[t] = (cnt / total) * idf
        return vec

    def _cosine(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(a.get(t, 0.0) * v for t, v in b.items())
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def query(self, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return [(doc_id, score)] sorted by descending similarity."""
        if not self._corpus:
            return []
        if self._dirty:
            self._build_idf()
        q_vec = self._tfidf_vec(_tokenize(text))
        scores = []
        for i, tokens in enumerate(self._corpus):
            d_vec = self._tfidf_vec(tokens)
            sim = self._cosine(q_vec, d_vec)
            if sim > 0:
                scores.append((self._ids[i], sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def embed_query(self, text: str) -> List[float]:
        """
        Produce a sparse 'pseudo-embedding' for TF-IDF retrieval.
        Returns empty list — TF-IDF retrieval is handled via query(), not dot-product.
        """
        return []


# ── Main embedding manager ─────────────────────────────────────────────────────

class EmbeddingManager:
    """
    Embedding manager with automatic fallback chain.

    Fallback order:
        local (fastembed BAAI/bge-small-en-v1.5)
        → openai (text-embedding-3-small)
        → cohere (embed-english-light-v3.0)
        → tfidf  (in-process, zero infra, always available)
    """

    PROVIDER_ORDER = ["local", "openai", "cohere", "tfidf"]

    def __init__(self, provider: str = "local", model_name: Optional[str] = None,
                 api_key: Optional[str] = None):
        self.requested_provider = provider
        self.active_provider = provider
        self.api_key = api_key
        self.model_name = self._default_model(provider, model_name)

        self._dense_model = None          # fastembed TextEmbedding
        self._openai_client = None
        self._cohere_client = None
        self._tfidf = TFIDFIndex()
        self._loaded = False

    def _default_model(self, provider: str, override: Optional[str]) -> str:
        if override:
            return override
        defaults = {
            "local": "BAAI/bge-small-en-v1.5",
            "openai": "text-embedding-3-small",
            "cohere": "embed-english-light-v3.0",
            "tfidf": "tfidf",
        }
        return defaults.get(provider, "tfidf")

    # ── load ──────────────────────────────────────────────────────────────────

    def _try_load_local(self) -> bool:
        try:
            from fastembed import TextEmbedding
            self._dense_model = TextEmbedding(model_name=self.model_name)
            logger.debug(f"[NeuroSleepNet] Embeddings: local ({self.model_name})")
            return True
        except ImportError:
            logger.warning("[NeuroSleepNet] fastembed not installed — falling back. "
                           "Install with: pip install neurosleepnet[local]")
        except Exception as e:
            logger.warning(f"[NeuroSleepNet] Local embedding load failed: {e}")
        return False

    def _try_load_openai(self) -> bool:
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.api_key)
            # Quick connectivity check
            self._openai_client.embeddings.create(input=["test"], model=self.model_name)
            logger.warning("[NeuroSleepNet] Embeddings: falling back to OpenAI")
            return True
        except Exception as e:
            logger.warning(f"[NeuroSleepNet] OpenAI embedding fallback failed: {e}")
        return False

    def _try_load_cohere(self) -> bool:
        try:
            import cohere
            self._cohere_client = cohere.Client(api_key=self.api_key or "")
            logger.warning("[NeuroSleepNet] Embeddings: falling back to Cohere")
            return True
        except Exception as e:
            logger.warning(f"[NeuroSleepNet] Cohere embedding fallback failed: {e}")
        return False

    def _activate_tfidf(self):
        logger.warning(
            "[NeuroSleepNet] All embedding providers unavailable — falling back to TF-IDF. "
            "Recall quality will degrade but the agent keeps running."
        )
        self.active_provider = "tfidf"
        self.model_name = "tfidf"

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True

        if self.requested_provider == "tfidf":
            self._activate_tfidf()
            return

        # Try requested provider first, then cascade
        start_idx = self.PROVIDER_ORDER.index(self.requested_provider) \
            if self.requested_provider in self.PROVIDER_ORDER else 0

        for provider in self.PROVIDER_ORDER[start_idx:]:
            if provider == "local":
                if self._try_load_local():
                    self.active_provider = "local"
                    return
            elif provider == "openai":
                if self._try_load_openai():
                    self.active_provider = "openai"
                    return
            elif provider == "cohere":
                if self._try_load_cohere():
                    self.active_provider = "cohere"
                    return
            elif provider == "tfidf":
                self._activate_tfidf()
                return

        self._activate_tfidf()

    # ── public API ────────────────────────────────────────────────────────────

    def embed(self, texts: List[str]) -> List[List[float]]:
        self._ensure_loaded()
        if not texts:
            return []

        if self.active_provider == "local" and self._dense_model:
            try:
                return [emb.tolist() for emb in self._dense_model.embed(texts)]
            except Exception as e:
                logger.warning(f"[NeuroSleepNet] Local embed failed mid-call: {e}. Switching to TF-IDF.")
                self.active_provider = "tfidf"

        if self.active_provider == "openai" and self._openai_client:
            try:
                resp = self._openai_client.embeddings.create(input=texts, model=self.model_name)
                return [item.embedding for item in resp.data]
            except Exception as e:
                logger.warning(f"[NeuroSleepNet] OpenAI embed failed: {e}. Switching to TF-IDF.")
                self.active_provider = "tfidf"

        if self.active_provider == "cohere" and self._cohere_client:
            try:
                resp = self._cohere_client.embed(texts=texts, model=self.model_name,
                                                  input_type="search_document")
                return list(resp.embeddings)
            except Exception as e:
                logger.warning(f"[NeuroSleepNet] Cohere embed failed: {e}. Switching to TF-IDF.")
                self.active_provider = "tfidf"

        # TF-IDF path — return empty vecs (retrieval done via tfidf.query())
        return [[] for _ in texts]

    def embed_single(self, text: str) -> List[float]:
        if not text.strip():
            return []
        results = self.embed([text])
        return results[0] if results else []

    def is_tfidf(self) -> bool:
        self._ensure_loaded()
        return self.active_provider == "tfidf"

    def tfidf_index(self) -> TFIDFIndex:
        """Return the TF-IDF index for population/query when dense embeds unavailable."""
        return self._tfidf

    def populate_tfidf(self, memories: List[dict]):
        """Seed the TF-IDF index from a list of memory dicts (id + content)."""
        for m in memories:
            self._tfidf.add(m["id"], m.get("content", ""))
