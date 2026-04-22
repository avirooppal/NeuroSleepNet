"""
LangChain adapter — three explicit tiers.

Tier 1 — AgentExecutor (Full Support, v1)
  Uses BaseCallbackHandler. Hooks tool_end, agent_finish, chain_end.
  Most reliable: one handler catches the full reasoning trace.

Tier 2 — LCEL Chains (Full Support, v1)
  Wraps .invoke() and .stream(). Memory injected via RunnableLambda.
  Streaming: async background buffer, zero blocking for caller.

Tier 3 — LangGraph (Experimental, v1 — node-wrapping only)
  LangGraph has no unified callback manager.
  Warns developer and falls back to wrapping individual node functions.
  Full graph support ships in v1.1.
"""
import asyncio
import logging
import threading
from typing import Any, Dict, List

from .base import AbstractAdapter
from ..context import safe_inject, build_injection_prefix, estimate_tokens

logger = logging.getLogger(__name__)

# ── Try LangChain imports ──────────────────────────────────────────────────────

try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema.agent import AgentFinish
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    BaseCallbackHandler = object  # Fallback base class

try:
    from langchain.agents import AgentExecutor as _AgentExecutor
    _HAS_AGENT_EXECUTOR = True
except ImportError:
    _AgentExecutor = None
    _HAS_AGENT_EXECUTOR = False


# ── Tier 1 — AgentExecutor callback handler ───────────────────────────────────

if _HAS_LANGCHAIN:
    class NSNCallbackHandler(BaseCallbackHandler):
        """
        Hooks into AgentExecutor's callback system to capture intermediate
        tool observations and final responses for memory storage.
        """

        def __init__(self, retrieve_fn, log_fn, query: str):
            super().__init__()
            self.retrieve_fn = retrieve_fn
            self.log_fn = log_fn
            self.query = query
            self._observations = []

        def on_tool_end(self, output: str, **kwargs: Any) -> None:
            """Store each tool observation — often the richest context."""
            try:
                self._observations.append(output)
                self.log_fn("", [], f"[Tool observation] {output[:500]}")
            except Exception:
                pass

        def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
            """Capture the final agent answer."""
            try:
                answer = str(finish.return_values.get("output", finish))
                self.log_fn(self.query, [], answer)
            except Exception:
                pass

        def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
            try:
                self.log_fn("", [], str(outputs))
            except Exception:
                pass
else:
    class NSNCallbackHandler:  # Stub when LangChain not installed
        def __init__(self, *args, **kwargs):
            pass


# ── Tier 1 Adapter — AgentExecutor ───────────────────────────────────────────

class LangChainCallbackAdapter(AbstractAdapter):
    """
    Tier 1: AgentExecutor — registers NSNCallbackHandler on the agent's
    callback list and injects memory into the initial input.
    """

    @classmethod
    def detect(cls, agent: Any) -> bool:
        if _HAS_AGENT_EXECUTOR and isinstance(agent, _AgentExecutor):
            return True
        class_name = type(agent).__name__
        return class_name == "AgentExecutor"

    def inject_memory(self, input_data: Any, memories: List[Dict], model_context_limit: int) -> Any:
        if not memories:
            return input_data

        query = str(input_data.get("input", input_data) if isinstance(input_data, dict) else input_data)
        existing_tokens = estimate_tokens(query)
        safe_mems = safe_inject(memories, existing_tokens, model_context_limit)
        if not safe_mems:
            return input_data

        prefix = build_injection_prefix(safe_mems)
        if isinstance(input_data, dict) and "input" in input_data:
            result = dict(input_data)
            result["input"] = f"{prefix}\n\n{input_data['input']}"
            return result
        return f"{prefix}\n\n{input_data}"

    def extract_response(self, response: Any) -> str:
        if isinstance(response, dict):
            return str(response.get("output", response))
        return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode="silent", model_context_limit=4096):
        original_invoke = agent.invoke

        def new_invoke(input_data, config=None, **kwargs):
            try:
                query = str(
                    input_data.get("input", input_data)
                    if isinstance(input_data, dict) else input_data
                )
                memories = retrieve_fn(query) if query else []
                augmented_input = self.inject_memory(input_data, memories, model_context_limit)

                # Register callback handler for trace capture
                if _HAS_LANGCHAIN:
                    handler = NSNCallbackHandler(retrieve_fn, log_fn, query)
                    if config is None:
                        config = {"callbacks": [handler]}
                    elif "callbacks" in config:
                        config["callbacks"].append(handler)
                    else:
                        config["callbacks"] = [handler]

                response = original_invoke(augmented_input, config=config, **kwargs)
                return response
            except Exception as exc:
                logger.error(f"[NSN LangChain Tier1] Error: {exc}")
                if fallback_mode == "raise":
                    raise
                return original_invoke(input_data, config=config, **kwargs)

        agent.invoke = new_invoke
        return agent


# ── Tier 2 Adapter — LCEL Chains ─────────────────────────────────────────────

class LCELAdapter(AbstractAdapter):
    """
    Tier 2: LCEL chains with .invoke() and .stream().
    Memory injected by prepending a RunnableLambda or augmenting the input dict.
    Streaming: tokens returned immediately; full response buffered in background.
    """

    @classmethod
    def detect(cls, agent: Any) -> bool:
        return (
            hasattr(agent, 'invoke')
            and hasattr(agent, 'stream')
            and not LangChainCallbackAdapter.detect(agent)  # Not Tier 1
        )

    def inject_memory(self, input_data: Any, memories: List[Dict], model_context_limit: int) -> Any:
        if not memories:
            return input_data
        query = str(input_data) if not isinstance(input_data, dict) else str(input_data)
        existing_tokens = estimate_tokens(query)
        safe_mems = safe_inject(memories, existing_tokens, model_context_limit)
        if not safe_mems:
            return input_data

        prefix = build_injection_prefix(safe_mems)
        if isinstance(input_data, str):
            return f"{prefix}\n\n{input_data}"
        if isinstance(input_data, dict):
            result = dict(input_data)
            key = next((k for k in ["input", "question", "query", "human_input"] if k in result), None)
            if key:
                result[key] = f"{prefix}\n\n{result[key]}"
            return result
        return input_data

    def extract_response(self, response: Any) -> str:
        if hasattr(response, 'content'):
            return response.content
        return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode="silent", model_context_limit=4096):
        original_invoke = agent.invoke
        original_stream = agent.stream

        def new_invoke(input_data, config=None, **kwargs):
            try:
                query = str(input_data)[:500]
                memories = retrieve_fn(query)
                augmented = self.inject_memory(input_data, memories, model_context_limit)
                response = original_invoke(augmented, config=config, **kwargs)
                log_fn(query, memories, self.extract_response(response))
                return response
            except Exception as exc:
                logger.error(f"[NSN LangChain Tier2] invoke error: {exc}")
                if fallback_mode == "raise":
                    raise
                return original_invoke(input_data, config=config, **kwargs)

        def new_stream(input_data, config=None, **kwargs):
            try:
                query = str(input_data)[:500]
                memories = retrieve_fn(query)
                augmented = self.inject_memory(input_data, memories, model_context_limit)
                stream = original_stream(augmented, config=config, **kwargs)

                def _buffer():
                    try:
                        full = ""
                        for chunk in stream:
                            full += self.extract_response(chunk)
                        log_fn(query, memories, full)
                    except Exception:
                        pass

                threading.Thread(target=_buffer, daemon=True).start()
                return stream
            except Exception as exc:
                logger.error(f"[NSN LangChain Tier2] stream error: {exc}")
                if fallback_mode == "raise":
                    raise
                return original_stream(input_data, config=config, **kwargs)

        agent.invoke = new_invoke
        agent.stream = new_stream
        return agent


# ── Tier 3 Adapter — LangGraph (Experimental) ────────────────────────────────

class LangGraphAdapter(AbstractAdapter):
    """
    Tier 3: LangGraph — EXPERIMENTAL in v1.

    LangGraph has no unified callback manager. astream_events API is not stable
    between v0.1 and v0.2. v1 strategy: wrap individual node functions.
    Full graph-level support ships in v1.1 after astream_events stabilises.
    """

    _EXPERIMENTAL_WARNING = (
        "\n[NSN Warning] LangGraph graph-level wrapping is EXPERIMENTAL in v1.\n"
        "For reliable integration, wrap individual node functions:\n"
        "    node_fn = nsn.wrap(node_fn)\n"
        "Full graph support ships in v1.1.\n"
    )

    @classmethod
    def detect(cls, agent: Any) -> bool:
        return (
            hasattr(agent, 'astream_events')
            and hasattr(agent, 'get_graph')
        )

    def inject_memory(self, input_data: Any, memories, model_context_limit: int) -> Any:
        return input_data  # Node-level wrapping handles injection

    def extract_response(self, response: Any) -> str:
        return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode="silent", model_context_limit=4096):
        import warnings
        warnings.warn(self._EXPERIMENTAL_WARNING, UserWarning, stacklevel=4)
        logger.warning(self._EXPERIMENTAL_WARNING)
        # For graph-level, we can only wrap __call__ and log
        original_call = getattr(agent, 'invoke', agent.__call__)

        def new_call(input_data, config=None, **kwargs):
            try:
                query = str(input_data)[:500]
                memories = retrieve_fn(query)
                # Node injection not possible at graph level — log only
                response = original_call(input_data, config=config, **kwargs) if config is not None else original_call(input_data, **kwargs)
                log_fn(query, memories, str(response))
                return response
            except Exception as exc:
                logger.error(f"[NSN LangGraph Tier3] Error: {exc}")
                if fallback_mode == "raise":
                    raise
                return original_call(input_data, **kwargs)

        if hasattr(agent, 'invoke'):
            agent.invoke = new_call
        return agent


# ── Unified detection ─────────────────────────────────────────────────────────

class LangChainAdapter(AbstractAdapter):
    """
    Unified entry point — detects which LangChain tier applies and delegates.
    Called from adapters/__init__.py get_adapter().
    """

    @classmethod
    def detect(cls, agent: Any) -> bool:
        module_name = getattr(agent.__class__, '__module__', '')
        return (
            "langchain" in module_name.lower()
            or hasattr(agent, 'invoke')
        )

    def inject_memory(self, *a, **kw):
        pass

    def extract_response(self, *a, **kw):
        pass

    def wrap_call(self, agent, retrieve_fn, log_fn, fallback_mode="silent", model_context_limit=4096):
        # Route to correct tier
        if LangChainCallbackAdapter.detect(agent):
            return LangChainCallbackAdapter().wrap_call(
                agent, retrieve_fn, log_fn, fallback_mode, model_context_limit
            )
        if LangGraphAdapter.detect(agent):
            return LangGraphAdapter().wrap_call(
                agent, retrieve_fn, log_fn, fallback_mode, model_context_limit
            )
        # Default to LCEL
        return LCELAdapter().wrap_call(
            agent, retrieve_fn, log_fn, fallback_mode, model_context_limit
        )
