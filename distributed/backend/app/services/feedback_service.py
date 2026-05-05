import logging
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models.memory import Memory

logger = logging.getLogger(__name__)

# Heuristic phrase matching for implicit feedback
POSITIVE_SIGNALS = [
    "thanks", "thank you", "perfect", "exactly", "correct", "right",
    "that's right", "yes", "great", "helpful", "got it", "makes sense",
    "that works", "good point",
]

NEGATIVE_SIGNALS = [
    "no, ", "wrong", "incorrect", "that's not", "that's wrong",
    "not what i", "you're wrong", "actually,", "no that", "that's not right",
    "i said", "i meant", "not quite", "no —",
]

class FeedbackService:
    @staticmethod
    def analyze_feedback_signal(text: str) -> Optional[float]:
        """
        Analyze text for implicit feedback signals.
        Returns:
            1.0 if positive signal found
            0.0 if negative signal found
            None if no clear signal found
        """
        if not text:
            return None
            
        text_lower = text.lower()
        
        # Check negative first (corrections usually more important)
        if any(signal in text_lower for signal in NEGATIVE_SIGNALS):
            return 0.0
            
        # Check positive
        if any(signal in text_lower for signal in POSITIVE_SIGNALS):
            return 1.0
            
        return None

    @staticmethod
    def ema_update(current_score: float, signal: float, access_count: int) -> float:
        """
        Alpha gets smaller as memory becomes more established.
        New memory (count=1): alpha=0.27 — shifts quickly
        Established memory (count=100): alpha=0.05 — very stable
        """
        alpha = max(0.05, 0.3 / (1 + access_count * 0.1))
        return (current_score * (1 - alpha)) + (signal * alpha)

    @staticmethod
    async def update_memory_feedback(
        session: AsyncSession,
        memory_ids: List[uuid.UUID],
        signal_value: float  # 1.0 for pos, 0.0 for neg
    ):
        """
        Update feedback_score using dynamic EMA.
        """
        if not memory_ids:
            return

        stmt = select(Memory).where(Memory.id.in_(memory_ids))
        result = await session.execute(stmt)
        memories = result.scalars().all()

        for mem in memories:
            # EMA Update with dynamic alpha
            mem.feedback_score = FeedbackService.ema_update(
                mem.feedback_score, 
                signal_value, 
                mem.access_count
            )
            mem.last_accessed_at = datetime.now(timezone.utc)
        
        await session.commit()
        logger.info(f"Updated feedback scores for {len(memories)} memories with signal {signal_value}")
