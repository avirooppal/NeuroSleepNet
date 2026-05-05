import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .embeddings import get_embedding


def normalize_recency(last_accessed_at: datetime) -> float:
    """
    Convert age to a 0.0-1.0 scale.
    Formula: 1.0 / (1.0 + log(1 + age_in_hours))
    Result: 0h -> 1.0 | 1h -> ~0.59 | 24h -> ~0.24 | 720h (1 mo) -> ~0.13
    """
    now = datetime.now(timezone.utc)
    if last_accessed_at.tzinfo is None:
        last_accessed_at = last_accessed_at.replace(tzinfo=timezone.utc)
    
    delta = now - last_accessed_at
    hours = max(0, delta.total_seconds() / 3600.0)
    
    # Using log(1 + hours) to dampen the decay curve
    return 1.0 / (1.0 + math.log(1 + hours))


DEFAULT_WEIGHTS = {"w_sim": 0.45, "w_rec": 0.15, "w_con": 0.25, "w_fb": 0.15}

def validate_weights(w: dict) -> dict:
    """
    Ensure weights sum to ~1.0. 
    If malformed or missing, fallback to DEFAULT_WEIGHTS.
    """
    if not w:
        return DEFAULT_WEIGHTS
        
    total = sum(w.values())
    if not (0.99 <= total <= 1.01):
        # We don't log directly here to keep it pure, but it will fallback
        return DEFAULT_WEIGHTS
    return w


def score_memory(
    similarity: float,
    recency: float,
    consolidation: float,
    feedback: float = 0.5,
    importance: float = 1.0,
    weights: dict = None
) -> float:
    """
    Composite scoring formula for re-ranking.
    All inputs (similarity, recency, consolidation, feedback) must be 0.0-1.0.
    Importance is a multiplier (0.5 to 2.0).
    """
    # Fix: Fail loudly/fallback if weights are malformed
    w = validate_weights(weights)
    
    base_score = (
        (similarity * w.get("w_sim", 0.45)) +
        (recency * w.get("w_rec", 0.15)) +
        (consolidation * w.get("w_con", 0.25)) +
        (feedback * w.get("w_fb", 0.15))
    )
    
    # Apply importance multiplier
    return base_score * importance


def generate_explanation(
    similarity: float,
    recency: float,
    consolidation: float,
    feedback: float = 0.0
) -> str:
    """
    Human-readable explanation of why a memory was retrieved.
    """
    reasons = []
    if similarity > 0.85:
        reasons.append("Exact semantic match")
    elif similarity > 0.6:
        reasons.append("High contextual relevance")
        
    if recency > 0.8:
        reasons.append("Fresh interaction")
        
    if feedback > 0.8:
        reasons.append("Strong human reinforcement")
    elif feedback < 0.3 and feedback != 0:
        reasons.append("Previously downweighted")
        
    if consolidation > 0.8:
        reasons.append("Core project knowledge")
        
    return " + ".join(reasons) if reasons else "General context"
