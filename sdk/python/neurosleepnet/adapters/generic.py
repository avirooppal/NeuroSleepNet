from typing import Any, List, Dict
from .base import AbstractAdapter, enforce_context_bounds, handle_streaming_response
import logging
import inspect

logger = logging.getLogger(__name__)

class GenericAdapter(AbstractAdapter):
    @classmethod
    def detect(cls, agent: Any) -> bool:
        # Fallback adapter that wraps any callable
        return callable(agent)

    def inject_memory(self, kwargs: Dict[str, Any], memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Injects memories into whatever text field exists, or prepends them in generically.
        If it's just a string argument or random kwargs, we try to safely append.
        """
        return kwargs

    def extract_response(self, response: Any) -> str:
        return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode: str = "silent", model_context_limit: int = 4096):
        original_call = getattr(agent, "__call__", agent) if callable(agent) else agent
        
        is_async = inspect.iscoroutinefunction(original_call)
        
        def new_call(*args, **kwargs):
            try:
                # Try to extract query from args
                query = str(args[0]) if args else ""
                memories = retrieve_fn(query) if query else []
                
                # Context math
                memories = enforce_context_bounds(query, memories, model_context_limit)
                
                # Context injection is tricky for black boxes. We assume a simple prepended string if it takes a string.
                if args and isinstance(args[0], str):
                    context = " ".join([m.get("content", "") for m in memories])
                    if context:
                        args = (f"Context: {context}\n\nQuery: {args[0]}",) + args[1:]
                
                res = original_call(*args, **kwargs)
                return handle_streaming_response(res, log_fn, query, memories, self.extract_response)

            except Exception as e:
                logger.error(f"NSN wrapping error for Generic Callable: {e}")
                if fallback_mode == "raise": raise
                return original_call(*args, **kwargs)

        async def async_new_call(*args, **kwargs):
            try:
                query = str(args[0]) if args else ""
                memories = retrieve_fn(query) if query else []
                memories = enforce_context_bounds(query, memories, model_context_limit)
                
                if args and isinstance(args[0], str):
                    context = " ".join([m.get("content", "") for m in memories])
                    if context:
                        args = (f"Context: {context}\n\nQuery: {args[0]}",) + args[1:]
                        
                res = await original_call(*args, **kwargs)
                return handle_streaming_response(res, log_fn, query, memories, self.extract_response)
                
            except Exception as e:
                logger.error(f"NSN wrapping error for Async Generic Callable: {e}")
                if fallback_mode == "raise": raise
                return await original_call(*args, **kwargs)
                
        return async_new_call if is_async else new_call
