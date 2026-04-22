"""
Anthropic Claude adapter for NeuroSleepNet.

Detection: hasattr(agent, 'messages') and hasattr(agent.messages, 'create')
Wraps: agent.messages.create() — both sync and async variants
Memory injected as a system prompt message prepended to the messages list.
Streaming: async background buffer, never blocks the caller's stream.
"""
import asyncio
import logging
import threading
from typing import Any, Dict, List

from .base import AbstractAdapter
from ..context import safe_inject, build_injection_prefix, estimate_tokens

logger = logging.getLogger(__name__)


class AnthropicAdapter(AbstractAdapter):
    """
    Adapter for Anthropic Claude clients (anthropic.Anthropic / anthropic.AsyncAnthropic).
    """

    @classmethod
    def detect(cls, agent: Any) -> bool:
        return (
            hasattr(agent, 'messages')
            and hasattr(getattr(agent, 'messages', None), 'create')
        )

    def inject_memory(self, messages: list, memories: List[Dict[str, Any]], model_context_limit: int) -> list:
        """Prepend a system message with memory context to the messages list."""
        if not memories:
            return messages

        # Estimate existing prompt size
        existing_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        safe_mems = safe_inject(memories, existing_tokens, model_context_limit)
        if not safe_mems:
            return messages

        prefix = build_injection_prefix(safe_mems)
        injected = list(messages)  # Never mutate original

        # Anthropic supports system role — use it when available
        # Prepend to existing system message if present, else insert new one
        if injected and injected[0].get("role") == "system":
            injected[0] = {
                "role": "system",
                "content": prefix + "\n\n" + injected[0]["content"],
            }
        else:
            injected.insert(0, {"role": "system", "content": prefix})

        return injected

    def extract_response(self, response: Any) -> str:
        # anthropic.types.Message has .content list of blocks
        if hasattr(response, 'content') and isinstance(response.content, list):
            return " ".join(
                block.text for block in response.content
                if hasattr(block, 'text')
            )
        if hasattr(response, 'content'):
            return str(response.content)
        return str(response)

    def wrap_call(
        self,
        agent: Any,
        retrieve_fn,
        log_fn,
        fallback_mode: str = "silent",
        model_context_limit: int = 200_000,
    ):
        original_create = agent.messages.create

        def new_create(*args, **kwargs):
            try:
                messages = list(kwargs.get("messages", args[0] if args else []))
                query = " ".join(
                    m.get("content", "") for m in messages
                    if m.get("role") == "user"
                )[-500:]  # Last 500 chars of user content for retrieval query

                memories = retrieve_fn(query) if query else []
                injected_messages = self.inject_memory(messages, memories, model_context_limit)

                # Handle streaming
                stream = kwargs.get("stream", False)
                if stream:
                    kwargs["messages"] = injected_messages
                    stream_obj = original_create(*args[1:] if args else [], **kwargs)

                    # Background buffer — never delay the stream
                    def _buffer_stream():
                        try:
                            full_response = ""
                            for event in stream_obj:
                                if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                                    full_response += event.delta.text
                            log_fn(query, memories, full_response)
                        except Exception:
                            pass

                    threading.Thread(target=_buffer_stream, daemon=True).start()
                    return stream_obj

                # Non-streaming
                if args:
                    args = (injected_messages,) + args[1:]
                else:
                    kwargs["messages"] = injected_messages

                response = original_create(*args, **kwargs)
                log_fn(query, memories, self.extract_response(response))
                return response

            except Exception as exc:
                logger.error(f"[NSN AnthropicAdapter] Wrapping error: {exc}")
                if fallback_mode == "raise":
                    raise
                return original_create(*args, **kwargs)

        agent.messages.create = new_create
        return agent
