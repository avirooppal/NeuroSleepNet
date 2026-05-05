from typing import List

from ..core.embeddings import get_embedding


class EmbeddingService:
    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        """
        Thin wrapper for core embedding logic.
        """
        return await get_embedding(text)


embedding_service = EmbeddingService()
