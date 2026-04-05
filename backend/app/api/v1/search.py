import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...schemas import memory as memory_schema
from ...services.memory_service import memory_service
from .auth import get_current_user

router = APIRouter()


@router.post("/", response_model=memory_schema.SearchResponse)
async def search_memories(
    search_in: memory_schema.MemorySearch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Search memories using Attention-based retrieval.
    Includes semantic similarity, recency decay, and consolidation importance.
    """
    results, residual_applied = await memory_service.search_memories(
        session=db,
        user=current_user,
        query=search_in.query,
        task_id=search_in.task_id,
        top_k=search_in.top_k,
        min_attention_score=search_in.min_attention_score
    )
    
    # Format the results to match SearchResponse
    formatted_results = []
    for res in results:
        mem = res["memory"]
        formatted_results.append(
            memory_schema.MemorySearchResult(
                **mem.__dict__,
                attention_score=res["attention_score"],
                why_retrieved=res["why_retrieved"]
            )
        )
        
    return {
        "memories": formatted_results,
        "sleep_last_run": None, # Should fetch from audit logs or separate sleep log
        "residual_context_applied": residual_applied
    }
