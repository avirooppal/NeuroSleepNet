import logging
import httpx
from typing import List

from ..config import settings
from ..utils.errors import NeuroSleepNetError

logger = logging.getLogger(__name__)

async def get_embedding(text: str) -> List[float]:
    """
    Get embedding for text using the embed sidecar service asynchronously.
    """
    if not text:
        return []

    url = f"{settings.EMBED_SERVICE_URL.rstrip('/')}/v1/embed"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json={"texts": [text]}, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return data["embeddings"][0]
    except Exception as e:
        logger.error(f"Failed to fetch embedding from sidecar: {e}")
        # Could fallback to dummy vectors for robustness in tests but raising is safer for DB parity
        raise NeuroSleepNetError(status_code=500, detail="Embedding service unavailable")
