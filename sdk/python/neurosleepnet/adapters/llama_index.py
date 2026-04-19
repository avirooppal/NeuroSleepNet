"""
LlamaIndex adapter for NeuroSleepNet.

Detection: (hasattr(agent, 'query') or hasattr(agent, 'chat'))
           and 'llama_index' in agent.__class__.__module__
Wraps: agent.query() and agent.chat() — memory injected as system prompt prefix.
"""
import logging
from typing import Any, Dict, List

from .base import AbstractAdapter
from ..context import safe_inject, build_injection_prefix, estimate_tokens

logger = logging.getLogger(__name__)


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

        prefix = build_injection_prefix(safe_mems)
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
