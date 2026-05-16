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
import threading
import numpy as np
from collections import Counter
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("neurosleepnet.embed")


# ── In-memory ANN embedding cache ─────────────────────────────────────────────

class EmbeddingCache:
    """
    Thread-safe in-memory ANN cache for NeuroSleepNet.

    Design decisions:
    - RLock + copy-on-write: rebuild() and _flush_locked() swap the matrix
      reference atomically. query() readers see a complete matrix, never a
      partial write.
    - List buffer in add(): avoids O(N) np.vstack on every remember() call.
      Vectors accumulate in self._pending and are merged in batches
      (every FLUSH_EVERY adds, or on query()).
    - Per-project instances: LocalStore maintains one cache per project key.
    """

    FLUSH_EVERY = 10  # flush pending buffer to matrix every N adds

    def __init__(self):
        self._lock = threading.RLock()
        self._matrix: Optional[np.ndarray] = None   # shape (N, D), L2-normalised
        self._ids: List[str] = []
        self._pending: List[Tuple[str, np.ndarray]] = []  # add() buffer

    def rebuild(self, rows: List[Tuple[str, bytes]]):
        """Full rebuild from (memory_id, embedding_blob) pairs. Copy-on-write."""
        if not rows:
            return
        new_ids = [r[0] for r in rows]
        vecs = [np.frombuffer(r[1], dtype=np.float32) for r in rows]
        mat = np.stack(vecs)                          # (N, D)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        new_mat = mat / norms                         # L2-normalised
        with self._lock:                              # atomic swap
            self._matrix = new_mat
            self._ids = new_ids
            self._pending = []                        # discard stale pending

    def add(self, memory_id: str, embedding: List[float]):
        """
        Buffer a new vector. Avoids O(N) vstack on every remember() call.
        Flushes to matrix automatically every FLUSH_EVERY adds.
        """
        vec = np.array(embedding, dtype=np.float32)
        n = np.linalg.norm(vec)
        if n > 0:
            vec = vec / n
        with self._lock:
            self._pending.append((memory_id, vec))
            if len(self._pending) >= self.FLUSH_EVERY:
                self._flush_locked()

    def _flush_locked(self):
        """Merge pending buffer into matrix. Caller must hold self._lock."""
        if not self._pending:
            return
        new_ids = [p[0] for p in self._pending]
        new_vecs = np.stack([p[1] for p in self._pending])
        if self._matrix is None:
            self._matrix = new_vecs
            self._ids = new_ids
        else:
            # copy-on-write: build new object, swap reference atomically
            self._matrix = np.vstack([self._matrix, new_vecs])
            self._ids = self._ids + new_ids
        self._pending = []

    def query(self, q_emb: List[float], top_k: int) -> List[Tuple[str, float]]:
        """
        Flush pending buffer then return [(id, cosine_score)] sorted descending.
        Pure matmul — no DB round-trip.
        """
        with self._lock:
            self._flush_locked()    # ensure all pending adds are visible
            mat = self._matrix
            ids = list(self._ids)
        if mat is None or not ids:
            return []
        q = np.array(q_emb, dtype=np.float32)
        qn = np.linalg.norm(q)
        if qn == 0:
            return []
        q = q / qn
        scores = mat @ q            # (N,) cosine scores, fast matmul
        k = min(top_k, len(scores))
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return [(ids[i], float(scores[i])) for i in top_idx]

    def size(self) -> int:
        with self._lock:
            return (len(self._ids) + len(self._pending))

    def invalidate(self):
        """Safely clear the matrix and pending buffer under lock."""
        with self._lock:
            self._matrix = None
            self._ids = []
            self._pending = []


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
    _CACHE_MAX = 512

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
        self._embed_cache: Dict[str, List[float]] = {}

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

        # Fix 3.3: Defer heavy model loading to background thread to avoid blocking init()
        def _load_in_background():
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

        threading.Thread(target=_load_in_background, daemon=True, name="NSN-EmbedLoader").start()

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

    def embed_single(self, text: str) -> Optional[List[float]]:
        """
        Embed a single text string, with LRU cache (P1-4).
        Cache key: MD5 of normalized text (strip + lower).
        Cache hit avoids the full model round-trip — critical for remember()
        calls on repeated/boilerplate content in tight agent loops.
        """
        import hashlib
        key = hashlib.md5(text.strip().lower().encode()).hexdigest()

        # Cache hit
        if key in self._embed_cache:
            return self._embed_cache[key]

        # Cache miss — compute
        result = self._embed_uncached(text)
        if result is not None:
            # Evict oldest if at capacity (dict insertion-order in Python 3.7+)
            if len(self._embed_cache) >= self._CACHE_MAX:
                self._embed_cache.pop(next(iter(self._embed_cache)))
            self._embed_cache[key] = result
        return result

    def _embed_uncached(self, text: str) -> Optional[List[float]]:
        """Raw embedding — called only on cache miss."""
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

    def cross_score(self, query: str, doc_text: str) -> float:
        """
        Lightweight cross-encoder proxy.
        Uses token-level intersection and density to provide a precision signal.
        """
        if not query or not doc_text:
            return 0.0
        # Use simple tokenize from this module
        import re
        def _local_tokenize(text):
            return re.findall(r"\b[a-z]{2,}\b", text.lower())
        
        q_tokens = set(_local_tokenize(query))
        d_tokens = set(_local_tokenize(doc_text))
        if not q_tokens:
            return 0.0
        intersection = q_tokens.intersection(d_tokens)
        # Ratio of query terms found in document
        return len(intersection) / len(q_tokens)
