"""
context.py — Model-family-aware memory context builder for NeuroSleepNet.

nsn.context() builds a memory injection string tuned to each model family's
known attention patterns. A Phi-3 model reads the top of the context window
best; a Mistral/Llama model benefits from structured XML in the system turn.
"""
from typing import Any, Dict, List

SAFETY_BUFFER_TOKENS = 256

# Known context limits (tokens) per model family / name substring
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # Long-context frontier
    "gpt-4.1":            1_000_000,
    "gemini-1.5":         1_000_000,
    "gemini":             1_000_000,
    "claude-3":             200_000,
    "claude":               200_000,
    "qwen2.5":              128_000,
    "gpt-4o":               128_000,
    "gpt-4-turbo":          128_000,
    "mistral-small-3":      128_000,
    "gemma-3":              128_000,
    "deepseek-r1":           64_000,
    "deepseek":              64_000,
    # Strong LLMs
    "gpt-4o-mini":           16_000,
    "gpt-4":                  8_192,
    "gpt-3.5-turbo":         16_385,
    "phi-4":                 16_384,
    "llama-3.1":             32_768,
    "llama-3":                8_192,
    "llama3":                 8_192,
    "llama2":                 4_096,
    "mistral-7b":             8_192,
    "mistral":                8_192,
    "mixtral":                8_192,
    "qwen2":                 32_768,
    "qwen-2":                32_768,
    "gemma-2":                8_192,
    "gemma":                  8_192,
    # SLMs
    "phi-3-mini":             4_096,
    "phi-3":                  4_096,
    "phi3":                   4_096,
    "phi-2":                  2_048,
    "phi-1":                  2_048,
    "llama-3.2-3b":           4_096,
    "llama-3.2-1b":           4_096,
    "qwen-1.5b":                512,
    "qwen-0.5b":                512,
    "tinyllama":               2_048,
    "smollm2":                 2_048,
    "smollm":                  2_048,
    "stable-lm":               4_096,
    "stablelm":                4_096,
}
DEFAULT_CONTEXT_LIMIT = 4096


def estimate_tokens(text: str) -> int:
    """
    P2-2: Token estimation with tiktoken when available.
    Falls back to word-split * 1.3 (better than len//4 for code/CJK/emoji).
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text.split()) * 1.3))


def get_model_context_limit(model_name: str) -> int:
    """
    P2-4: Look up context window for a model.
    NSN_MODEL_LIMIT env var overrides all registry values.
    """
    import os
    env_override = os.environ.get("NSN_MODEL_LIMIT")
    if env_override:
        try:
            return int(env_override)
        except ValueError:
            pass
    if not model_name:
        return DEFAULT_CONTEXT_LIMIT
    name = model_name.lower()
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key in name:
            return limit
    return DEFAULT_CONTEXT_LIMIT


def classify_model_strength(model_name: str) -> str:
    if not model_name:
        return "STRONG"
    name = model_name.lower()
    weak = ["tiny", "smol", "qwen-0.5", "qwen-1.5", "phi-1", "phi-2",
            "phi-3-mini", "llama-3.2-1b", "llama-3.2-3b"]
    return "WEAK" if any(p in name for p in weak) else "STRONG"


def get_recommended_settings(strength: str) -> Dict[str, Any]:
    if strength == "WEAK":
        # Lenient threshold for SLMs, less context to avoid distraction
        return {
            "top_k": 3,
            "min_score": 0.32,
            "strict_prompting": True,
            "memory_window": 1024
        }
    # Strict threshold for strong models, more context for reasoning
    return {
        "top_k": 5,
        "min_score": 0.55,
        "strict_prompting": False,
        "memory_window": 4096
    }


# ── Model-family format templates ─────────────────────────────────────────────

def _fmt_xml(memories: List[Dict], include_scores: bool = False) -> str:
    parts = ["<memory_context>"]
    for i, m in enumerate(memories, 1):
        score = m.get("attention_score", 0.0)
        mid = str(m.get("id", ""))[:8]
        mtype = m.get("memory_type", "semantic")
        pinned = " pinned=\"true\"" if m.get("pinned") else ""
        score_attr = f" score=\"{score:.2f}\"" if include_scores else ""
        parts.append(f'  <memory index="{i}" type="{mtype}" id="{mid}"{pinned}{score_attr}>')
        parts.append(f'    {m.get("content", "")}')
        parts.append("  </memory>")
    parts.append("</memory_context>")
    return "\n".join(parts)


def _fmt_markdown(memories: List[Dict]) -> str:
    parts = ["## Recalled Memory Context", ""]
    for i, m in enumerate(memories, 1):
        mtype = m.get("memory_type", "semantic")
        pin_tag = " 📌" if m.get("pinned") else ""
        parts.append(f"**[{i}]** `{mtype}`{pin_tag}")
        parts.append(m.get("content", ""))
        parts.append("")
    parts.append("---")
    return "\n".join(parts)


def _fmt_plain(memories: List[Dict]) -> str:
    parts = ["[MEMORY CONTEXT START]"]
    for i, m in enumerate(memories, 1):
        parts.append(f"[{i}] {m.get('content', '')}")
    parts.append("[MEMORY CONTEXT END]")
    return "\n".join(parts)


# ── Model-family injection position templates ─────────────────────────────────

MODEL_FAMILY_TEMPLATES = {
    # Phi-3: responds best to structured context at the very top of the prompt
    "phi3": {
        "position": "top",
        "prefix": "IMPORTANT: PREVIOUS CONTEXT FROM LONG-TERM MEMORY\n--------------------------------------------------\n",
        "suffix": "\n--------------------------------------------------\nUse the above memory to answer the current request.\n\n",
        "default_format": "plain",
    },
    # Mistral: instruction-tuned, benefits from XML in system role
    "mistral": {
        "position": "system",
        "prefix": "SYSTEM: Use the following memory context to inform your response:\n",
        "suffix": "\n",
        "default_format": "xml",
    },
    # Gemma: structured markdown works well in the human turn
    "gemma": {
        "position": "top",
        "prefix": "",
        "suffix": "\n\n",
        "default_format": "markdown",
    },
    # Llama-3: responds well to system-role XML
    "llama3": {
        "position": "top",
        "prefix": "### USER MEMORY & CONTEXT\nThe following facts are retrieved from your long-term memory. Use them to provide a personalized response:\n",
        "suffix": "\n### END OF CONTEXT\n\n",
        "default_format": "markdown",
    },
    # Generic fallback
    "generic": {
        "position": "top",
        "prefix": "### Memory Context\n",
        "suffix": "\n\n",
        "default_format": "markdown",
    },
}


def build_context(
    memories: List[Dict],
    query: str = "",
    max_tokens: int = 512,
    model_family: str = "generic",
    fmt: str = "auto",
    include_pins: bool = True,
) -> str:
    """
    Build a memory injection string for a given model family.
    Pins are always injected first. Non-pinned memories fill remaining budget.
    """
    if not memories:
        return ""

    template = MODEL_FAMILY_TEMPLATES.get(model_family, MODEL_FAMILY_TEMPLATES["generic"])
    if fmt == "auto":
        fmt = template["default_format"]

    # Separate pins
    pins = [m for m in memories if m.get("pinned")] if include_pins else []
    rest = [m for m in memories if not m.get("pinned")]
    ordered = pins + rest

    # Token budget: select memories that fit
    budget = max_tokens - estimate_tokens(template["prefix"]) - estimate_tokens(template["suffix"])
    selected: List[Dict] = []
    used = 0
    for m in ordered:
        cost = estimate_tokens(m.get("content", ""))
        if used + cost <= budget:
            selected.append(m)
            used += cost
        elif m.get("pinned"):
            selected.append(m)  # pins always included even if over budget

    if not selected:
        return ""

    if fmt == "xml":
        body = _fmt_xml(selected)
    elif fmt == "markdown":
        body = _fmt_markdown(selected)
    else:
        body = _fmt_plain(selected)

    return template["prefix"] + body + template["suffix"]


def safe_inject(memories: List[Dict], existing_prompt_tokens: int,
                model_context_limit: int) -> List[Dict]:
    """Select memories that fit within context budget without truncating."""
    available = model_context_limit - existing_prompt_tokens - SAFETY_BUFFER_TOKENS
    if available <= 0:
        return []
    ranked = sorted(memories, key=lambda m: (m.get("pinned", False), m.get("attention_score", 0.0)), reverse=True)
    injected, used = [], 0
    for m in ranked:
        cost = estimate_tokens(m.get("content", ""))
        if used + cost <= available:
            injected.append(m)
            used += cost
    return injected
