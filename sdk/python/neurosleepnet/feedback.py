"""
feedback.py — Explicit and implicit feedback engine for NeuroSleepNet.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("neurosleepnet.feedback")

# Correction/contradiction signals in follow-up turns
NEGATIVE_SIGNALS = [
    "no,", "no.", "that's wrong", "that's incorrect", "actually,", "actually.",
    "you're wrong", "not correct", "wrong,", "wrong.", "incorrect",
    "i said", "i meant", "what i said", "that's not what", "please re-read",
    "you forgot", "you missed", "you didn't", "try again", "that's not right",
]
POSITIVE_SIGNALS = [
    "yes", "correct", "exactly", "right", "perfect", "great", "good",
    "that's right", "that's correct", "thanks", "thank you", "makes sense",
    "you remembered", "you got it", "spot on",
]


def score_implicit(follow_up: str) -> float:
    """
    Score a follow-up turn for implicit feedback signal.
    Returns: +1.0 (positive), -1.0 (negative), 0.0 (neutral)
    """
    text = follow_up.lower().strip()
    if any(sig in text for sig in NEGATIVE_SIGNALS):
        return -1.0
    if any(sig in text for sig in POSITIVE_SIGNALS):
        return 1.0
    return 0.0


def apply_implicit_feedback(store, project: str, memories: List[Dict], follow_up: str):
    """
    Called by nsn.wrap() after observing the next user turn.
    Upweights or downweights the memories that were injected.
    """
    if not memories or not follow_up:
        return
    signal = score_implicit(follow_up)
    if signal == 0.0:
        return
    helpful = signal > 0.0
    for mem in memories:
        mid = mem.get("id")
        if not mid:
            continue
        try:
            store.update_feedback(memory_id=mid, project=project, helpful=helpful)
            logger.debug(f"[NeuroSleepNet] Implicit feedback ({'positive' if helpful else 'negative'}) applied to {mid[:8]}")
        except Exception as e:
            logger.debug(f"[NeuroSleepNet] Implicit feedback failed for {mid[:8]}: {e}")
