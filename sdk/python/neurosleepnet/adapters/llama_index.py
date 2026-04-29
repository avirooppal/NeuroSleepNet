"""
LlamaIndex adapter for NeuroSleepNet.

Detection: (hasattr(agent, 'query') or hasattr(agent, 'chat'))
           and 'llama_index' in agent.__class__.__module__
Wraps: agent.query() and agent.chat() — memory injected as system prompt prefix.
"""
import logging
from typing import Any, Dict, List

from .base import AbstractAdapter
from ..context import safe_inject, build_context, estimate_tokens

logger = logging.getLogger(__name__)

try:
    from llama_index.core.memory import BaseMemory
    from llama_index.core.llms import ChatMessage
    _HAS_LLAMA_INDEX = True
except ImportError:
    _HAS_LLAMA_INDEX = False
    BaseMemory = object
    ChatMessage = object


class LlamaIndexAdapter(AbstractAdapter):

    @classmethod
    def detect(cls, agent: Any) -> bool:
        module = getattr(agent.__class__, '__module__', '')
        return (
            'llama_index' in module
            and (hasattr(agent, 'query') or hasattr(agent, 'chat'))
        )

    def inject_memory(self, query_str: str, memories: List[Dict[str, Any]], model_context_limit: int) -> str:
        """Prepend memory context to a query string."""
        if not memories:
            return query_str

        existing_tokens = estimate_tokens(query_str)
        safe_mems = safe_inject(memories, existing_tokens, model_context_limit)
        if not safe_mems:
            return query_str

        prefix = build_context(safe_mems)
        return f"{prefix}\n\nQuery: {query_str}"

    def extract_response(self, response: Any) -> str:
        # LlamaIndex Response objects have .response string
        if hasattr(response, 'response'):
            return str(response.response)
        return str(response)

    def wrap_call(
        self,
        agent: Any,
        retrieve_fn,
        log_fn,
        fallback_mode: str = "silent",
        model_context_limit: int = 4_096,
    ):
        # Wrap .query() if available
        if hasattr(agent, 'query'):
            original_query = agent.query

            def new_query(query_str: str, **kwargs):
                try:
                    memories = retrieve_fn(query_str)
                    augmented = self.inject_memory(query_str, memories, model_context_limit)
                    response = original_query(augmented, **kwargs)
                    log_fn(query_str, memories, self.extract_response(response))
                    return response
                except Exception as exc:
                    logger.error(f"[NSN LlamaIndexAdapter] query error: {exc}")
                    if fallback_mode == "raise":
                        raise
                    return original_query(query_str, **kwargs)

            agent.query = new_query

        # Wrap .chat() if available
        if hasattr(agent, 'chat'):
            original_chat = agent.chat

            def new_chat(message: str, **kwargs):
                try:
                    memories = retrieve_fn(message)
                    augmented = self.inject_memory(message, memories, model_context_limit)
                    response = original_chat(augmented, **kwargs)
                    log_fn(message, memories, self.extract_response(response))
                    return response
                except Exception as exc:
                    logger.error(f"[NSN LlamaIndexAdapter] chat error: {exc}")
                    if fallback_mode == "raise":
                        raise
                    return original_chat(message, **kwargs)

            agent.chat = new_chat

        return agent


# ── LlamaIndex BaseMemory Bridge ──────────────────────────────────────────────

if _HAS_LLAMA_INDEX:
    class NSNMemory(BaseMemory):
        """
        A native LlamaIndex memory implementation that uses NeuroSleepNet.
        """
        user_id: str = "default"
        recall_threshold: float = 0.5
        
        def get(self, input_str: Optional[str] = None, **kwargs: Any) -> List[ChatMessage]:
            import nsn
            if not input_str:
                return []
            
            memories = nsn.recall(str(input_str), user_id=self.user_id, min_score=self.recall_threshold)
            
            messages = []
            for m in memories:
                role = "assistant" if m.get("type") == "agent" else "user"
                messages.append(ChatMessage(role=role, content=m["content"]))
            return messages

        def put(self, message: ChatMessage) -> None:
            import nsn
            m_type = "agent" if message.role == "assistant" else "episodic"
            nsn.remember(message.content, user_id=self.user_id, type=m_type)

        def reset(self) -> None:
            pass
else:
    class NSNMemory:
        def __init__(self, *args, **kwargs):
            raise ImportError("LlamaIndex is required for NSNMemory adapter.")
