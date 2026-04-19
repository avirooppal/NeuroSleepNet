"""
Ollama adapter for NeuroSleepNet.

Detection: hasattr(agent, 'generate') and hasattr(agent, 'chat')
Wraps: agent.chat() — memory injected into the messages list.
Both sync and async clients supported.
"""
import logging
import threading
from typing import Any, Dict, List

from .base import AbstractAdapter
from ..context import safe_inject, build_injection_prefix, estimate_tokens

logger = logging.getLogger(__name__)


class OllamaAdapter(AbstractAdapter):
    """
    Adapter for ollama-python clients (ollama.Client / ollama.AsyncClient).
    """

    @classmethod
    def detect(cls, agent: Any) -> bool:
        return (
            hasattr(agent, 'generate')
            and hasattr(agent, 'chat')
        )

    def inject_memory(self, messages: list, memories: List[Dict[str, Any]], model_context_limit: int) -> list:
        """Prepend memory context into Ollama messages list."""
        if not memories:
            return messages

        existing_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
        safe_mems = safe_inject(memories, existing_tokens, model_context_limit)
        if not safe_mems:
            return messages

        prefix = build_injection_prefix(safe_mems)
        injected = list(messages)  # Copy — never mutate original

        # Prepend system message (Ollama supports role=system)
        if injected and injected[0].get("role") == "system":
            injected[0] = {
                "role": "system",
                "content": prefix + "\n\n" + injected[0]["content"],
            }
        else:
            injected.insert(0, {"role": "system", "content": prefix})

        return injected

    def extract_response(self, response: Any) -> str:
        # ollama response dict: response['message']['content']
        if isinstance(response, dict):
            return response.get("message", {}).get("content", str(response))
        if hasattr(response, 'message'):
            msg = response.message
            return getattr(msg, 'content', str(msg))
        return str(response)

    def wrap_call(
        self,
        agent: Any,
        retrieve_fn,
        log_fn,
        fallback_mode: str = "silent",
        model_context_limit: int = 8_192,  # Ollama defaults vary — 8k is conservative
    ):
        original_chat = agent.chat

        def new_chat(*args, **kwargs):
            try:
                messages = list(kwargs.get("messages", args[1] if len(args) > 1 else []))
                query = " ".join(
                    str(m.get("content", "")) for m in messages
                    if m.get("role") == "user"
                )[-500:]

                memories = retrieve_fn(query) if query else []
                injected_messages = self.inject_memory(messages, memories, model_context_limit)

                stream = kwargs.get("stream", False)
                if stream:
                    kwargs["messages"] = injected_messages
                    stream_obj = original_chat(*args, **kwargs)

                    def _buffer():
                        try:
                            full = ""
                            for chunk in stream_obj:
                                if isinstance(chunk, dict):
                                    full += chunk.get("message", {}).get("content", "")
                                elif hasattr(chunk, 'message'):
                                    full += getattr(chunk.message, 'content', '')
                            log_fn(query, memories, full)
                        except Exception:
                            pass

                    threading.Thread(target=_buffer, daemon=True).start()
                    return stream_obj

                kwargs["messages"] = injected_messages
                response = original_chat(*args, **kwargs)
                log_fn(query, memories, self.extract_response(response))
                return response

            except Exception as exc:
                logger.error(f"[NSN OllamaAdapter] Wrapping error: {exc}")
                if fallback_mode == "raise":
                    raise
                return original_chat(*args, **kwargs)

        agent.chat = new_chat
        return agent
