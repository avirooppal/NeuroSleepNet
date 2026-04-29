"""
Celery task definitions for the `embed` queue.

Queue: embed
Workers: auto-scaling (hot path — every memory write triggers embedding)
These tasks are IO-bound against the fastembed sidecar (http://nsn-embed:8001).
"""
import logging
import os

import httpx

from ..celery_app import celery_app

logger = logging.getLogger(__name__)

EMBED_SERVICE_URL = os.environ.get("EMBED_SERVICE_URL", "http://nsn-embed:8001")


def _call_embed_service(texts: list[str]) -> list[list[float]]:
    """Call the fastembed sidecar and return embedding vectors."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{EMBED_SERVICE_URL}/v1/embed", json={"texts": texts})
        resp.raise_for_status()
        return resp.json()["embeddings"]


@celery_app.task(name="tasks.embed.generate", bind=True, max_retries=3, default_retry_delay=5)
def generate_embedding(self, memory_id: str):
    """
    Generate and store the embedding for a single memory.
    Called after a memory is written to DB (embedding is not blocking the write).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    engine = create_engine(db_url)

    with Session(engine) as session:
        from ...models.memory import Memory
        mem = session.get(Memory, memory_id)
        if not mem:
            logger.warning(f"[Embed] Memory {memory_id} not found — skipping.")
            return

        try:
            [embedding] = _call_embed_service([mem.content])
            mem.embedding = embedding
            session.commit()
            logger.debug(f"[Embed] Embedded memory {memory_id} ({len(embedding)}d)")
            return {"memory_id": memory_id, "dim": len(embedding)}
        except Exception as exc:
            logger.error(f"[Embed] Failed to embed memory {memory_id}: {exc}")
            raise self.retry(exc=exc)


@celery_app.task(name="tasks.embed.batch_generate", bind=True, max_retries=3, default_retry_delay=5)
def batch_generate_embeddings(self, memory_ids: list[str]):
    """
    Generate embeddings for a batch of memories (from POST /v1/memories/batch).
    Calls embed service once for the entire batch — significantly more efficient.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    engine = create_engine(db_url)

    with Session(engine) as session:
        from ...models.memory import Memory
        memories = session.execute(
            select(Memory).where(Memory.id.in_(memory_ids))
        ).scalars().all()

        if not memories:
            return {"embedded": 0}

        texts = [m.content for m in memories]
        try:
            embeddings = _call_embed_service(texts)
            for mem, emb in zip(memories, embeddings):
                mem.embedding = emb
            session.commit()
            logger.info(f"[Embed] Batch embedded {len(memories)} memories.")
            return {"embedded": len(memories)}
        except Exception as exc:
            logger.error(f"[Embed] Batch embedding failed: {exc}")
            raise self.retry(exc=exc)
