import logging
from typing import List, Optional

from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from ..config import settings
from ..utils.errors import EmbeddingUnavailableError

logger = logging.getLogger(__name__)

# Lazy initialization of local model to save memory if not needed
_local_model: Optional[SentenceTransformer] = None


def get_local_model() -> SentenceTransformer:
    global _local_model
    if _local_model is None:
        logger.info("Initializing local embedding model (sentence-transformers)...")
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _local_model


async def get_embedding(text: str) -> List[float]:
    """
    Get embedding for text using OpenAI primary and local fallback.
    """
    try:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
            logger.warning("OpenAI API key not set, skipping to fallback.")
            raise ValueError("No API key")

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Primary embedding failed: {e}. Attempting local fallback.")
        try:
            model = get_local_model()
            # MiniLM-L6-v2 produces 384 dimensions. 
            # text-embedding-3-small produces 1536.
            # We need to handle this discrepancy.
            # For this prototype, we'll pad or truncate, or just log the mismatch.
            # Correct approach: map to a fixed dimension if possible, 
            # or ensure the DB column matches.
            # pgvector column is VECTOR(1536).
            embedding = model.encode(text).tolist()
            
            # PADDING to 1536 for compatibility with pgvector column
            if len(embedding) < 1536:
                embedding.extend([0.0] * (1536 - len(embedding)))
            return embedding[:1536]
        except Exception as local_e:
            logger.error(f"Fallback embedding failed: {local_e}")
            raise EmbeddingUnavailableError("Both embedding providers failed")
