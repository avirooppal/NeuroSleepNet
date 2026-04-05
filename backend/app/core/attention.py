import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .embeddings import get_embedding


def compute_recency_weight(last_accessed_at: datetime) -> float:
    """
    Decay weight based on time since last access.
    Halflife of 7 days (default).
    """
    now = datetime.now(timezone.utc)
    # Ensure timezone awareness
    if last_accessed_at.tzinfo is None:
        last_accessed_at = last_accessed_at.replace(tzinfo=timezone.utc)
    
    delta = now - last_accessed_at
    days = delta.total_seconds() / (24 * 3600)
    
    # Simple exponential decay: 0.5 ^ (days / halflife)
    # Halflife = 7 days
    return math.pow(0.5, days / 7.0)


def score_memory(
    cosine_similarity: float,
    recency_weight: float,
    consolidation_score: float
) -> float:
    """
    Aggregate score for ranking.
    """
    # 0 -> 1.0 range
    return cosine_similarity * recency_weight * consolidation_score


def generate_explanation(
    cosine_similarity: float,
    recency_weight: float,
    consolidation_score: float
) -> str:
    """
    Human-readable explanation of why a memory was retrieved.
    """
    reasons = []
    if cosine_similarity > 0.8:
        reasons.append(f"High semantic similarity ({cosine_similarity:.2f})")
    elif cosine_similarity > 0.5:
        reasons.append(f"Moderate similarity ({cosine_similarity:.2f})")
        
    if recency_weight > 0.8:
        reasons.append("Recently accessed")
    elif recency_weight < 0.2:
        reasons.append("Old/Stale memory")
        
    if consolidation_score > 0.8:
        reasons.append("Highly consolidated/Important")
    elif consolidation_score < 0.3:
        reasons.append("Fragile/At-risk memory")
        
    return " + ".join(reasons) if reasons else "Generic relevance"
