"""
Context window math and safe memory injection.

Before every injection, available token budget is calculated and memories are
inserted in attention-score order until the budget is exhausted. A memory is
never truncated mid-way — corrupting mid-memory content is worse than omitting it.

SAFETY_BUFFER_TOKENS is always reserved for the model's response generation.
"""
from typing import List, Dict, Any

# ── Safety constant ────────────────────────────────────────────────────────────
SAFETY_BUFFER_TOKENS = 256  # Always reserved for response generation

# ── Model default context limits ──────────────────────────────────────────────
# User-overridable via nsn.wrap(agent, model_context_limit=N)
# or nsn.init(model_context_limit=N)

MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # Ultra-small SLMs
    "qwen-0.5b":           512,
    "qwen-1.5b":           512,
    "tinyllama-1.1b":    2_048,
    "smollm":            2_048,
    "smollm2":           2_048,
    # Small / medium
    "llama-3.2-3b":      4_096,
    "llama-3.2-3b-instruct": 4_096,
    "mistral-7b":        8_192,
    "mistral-7b-instruct": 8_192,
    "llama-3.1-8b":     16_384,
    "llama-3.1-8b-instruct": 16_384,
    "llama-3.1-70b":    16_384,
    # Large / frontier
    "gpt-4o":          128_000,
    "gpt-4o-mini":     128_000,
    "gpt-4-turbo":     128_000,
    "gpt-3.5-turbo":    16_385,
    "claude-3-opus":   200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku":  200_000,
    "claude-3-5-sonnet": 200_000,
    "gemini-1.5-pro":1_000_000,
    "gemini-1.5-flash":1_000_000,
}

DEFAULT_CONTEXT_LIMIT = 4_096  # Conservative fallback for unknown models


def estimate_tokens(text: str) -> int:
    """
    Fast token count approximation — 4 chars ≈ 1 token for English text.
    Never import tiktoken here — this runs on the hot path for every agent call.
    For exact counts, use tiktoken in the background; here we need sub-ms speed.
    """
    return max(1, len(text) // 4)


def get_model_context_limit(model_name: str) -> int:
    """
    Look up the default context limit for a model family.
    Case-insensitive, partial-match friendly.
    """
    if not model_name:
        return DEFAULT_CONTEXT_LIMIT
    name_lower = model_name.lower()
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key in name_lower or name_lower in key:
            return limit
    return DEFAULT_CONTEXT_LIMIT


def safe_inject(
    memories: List[Dict[str, Any]],
    existing_prompt_tokens: int,
    model_context_limit: int,
) -> List[Dict[str, Any]]:
    """
    Select memories to inject without overflowing the model's context window.

    Rules (non-negotiable):
    - Always reserve SAFETY_BUFFER_TOKENS for response generation
    - Sort by attention_score descending — highest relevance first
    - Never truncate a memory mid-way — include it fully or skip it entirely
    - Return empty list (not an error) if there's no room

    Args:
        memories:               Retrieved memories with 'content' and 'attention_score' fields.
        existing_prompt_tokens: Token count of the base prompt before injection.
        model_context_limit:    Hard limit for this model (from init() or model table).

    Returns:
        Ordered list of memories that fit within budget.
    """
    available = model_context_limit - existing_prompt_tokens - SAFETY_BUFFER_TOKENS

    if available <= 0:
        return []

    # Sort by attention score — most relevant first
    ranked = sorted(
        memories,
        key=lambda m: m.get("attention_score", m.get("consolidation_score", 0.0)),
        reverse=True,
    )

    injected, used = [], 0
    for memory in ranked:
        content = memory.get("content", "")
        token_count = memory.get("token_count", estimate_tokens(content))
        if used + token_count <= available:
            injected.append(memory)
            used += token_count
        # else: skip — never truncate mid-memory

    return injected


def build_injection_prefix(memories: List[Dict[str, Any]], delimiter: str = "\n---\n") -> str:
    """
    Build the memory injection string to prepend to a prompt.
    Format is intentionally simple — models read it reliably across families.
    """
    if not memories:
        return ""

    parts = ["[RELEVANT MEMORY CONTEXT]"]
    for i, mem in enumerate(memories, 1):
        content = mem.get("content", "")
        score = mem.get("attention_score", mem.get("consolidation_score", 0.0))
        parts.append(f"Memory {i} (relevance: {score:.2f}):\n{content}")

    parts.append("[END MEMORY CONTEXT]")
    return delimiter.join(parts)
