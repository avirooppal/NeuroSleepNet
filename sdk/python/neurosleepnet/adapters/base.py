from abc import ABC, abstractmethod
from typing import Any, List, Dict
import inspect
import logging

logger = logging.getLogger(__name__)

def enforce_context_bounds(query: str, memories: List[Dict[str, Any]], max_limit: int) -> List[Dict[str, Any]]:
    """Truncates the lowest scoring memories to prevent exceeding context window."""
    if not memories:
        return []
        
    query_tokens = len(query) // 4
    current_tokens = query_tokens
    accepted_memories = []
    
    # Needs to be sorted by importance or attention score, assume it comes pre-sorted from RAG
    for m in memories:
        mem_tokens = len(str(m.get("content", ""))) // 4
        if current_tokens + mem_tokens < max_limit:
            accepted_memories.append(m)
            current_tokens += mem_tokens
        else:
            logger.warning(f"Dropping memory due to context window bounds (limit: {max_limit})")
            
    return accepted_memories

def handle_streaming_response(res: Any, log_fn, query: str, memories: list, extract_fn):
    """Transparently buffers a stream for logging without blocking the caller."""
    if inspect.isgenerator(res):
        def sync_proxy(gen):
            chunks = []
            for chunk in gen:
                parts = extract_fn(chunk)
                if parts: chunks.append(parts)
                yield chunk
            log_fn(query, memories, "".join(chunks))
        return sync_proxy(res)
        
    elif inspect.isasyncgen(res):
        async def async_proxy(gen):
            chunks = []
            async for chunk in gen:
                parts = extract_fn(chunk)
                if parts: chunks.append(parts)
                yield chunk
            log_fn(query, memories, "".join(chunks))
        return async_proxy(res)
        
    else:
        log_fn(query, memories, extract_fn(res))
        return res

class AbstractAdapter(ABC):
    @classmethod
    @abstractmethod
    def detect(cls, agent: Any) -> bool:
        """
        Returns True if this adapter is capable of wrapping the given agent.
        """
        pass

    @abstractmethod
    def inject_memory(self, *args, memories: List[Dict[str, Any]], **kwargs) -> Any:
        """
        Takes the original arguments and injects the retrieved memories into the context window.
        Returns the modified args/kwargs.
        """
        pass

    @abstractmethod
    def extract_response(self, response: Any) -> str:
        """
        Extracts the plain text response from the model's specific output format.
        Useful for logging what the model actually outputted to evaluate memory effectiveness.
        """
        pass

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode: str = "silent", model_context_limit: int = 4096, strict: bool = False, model_strength: str = "STRONG"):
        """
        The core wrapping logic. 
        Implementations should override this to properly wrap the __call__, .invoke(), 
        or .create() methods depending on the framework.
        """
        pass
