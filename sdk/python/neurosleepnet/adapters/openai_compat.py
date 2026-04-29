from typing import Any, List, Dict
from .base import AbstractAdapter
from ..context import build_context
import logging

logger = logging.getLogger(__name__)

class OpenAIAdapter(AbstractAdapter):
    @classmethod
    def detect(cls, agent: Any) -> bool:
        # Detect if it's an OpenAI client instance or a completions class
        cls_name = agent.__class__.__name__
        module_name = agent.__class__.__module__
        return "openai" in module_name.lower() or cls_name == "OpenAI"

    def inject_memory(self, kwargs: Dict[str, Any], memories: List[Dict[str, Any]], strict: bool = False) -> Dict[str, Any]:
        """
        Injects memories as a structured block.
        """
        if not memories:
            return kwargs
            
        system_content = build_context(memories)
        
        if strict:
            strict_prefix = (
                "You are an agent with persistent long-term memory. "
                "Use ONLY the provided context below to answer. "
                "If the answer is not in the context, say 'NOT FOUND'. "
                "Do not hallucinate or use external knowledge for these facts.\n\n"
            )
            system_content = strict_prefix + system_content
            
            # Enforce deterministic behavior in kwargs
            kwargs["temperature"] = 0.0
            kwargs["top_p"] = 1.0
            # Optional: cap max_tokens if not set
            if "max_tokens" not in kwargs:
                kwargs["max_tokens"] = 512

        system_msg = {"role": "system", "content": system_content}
        messages = kwargs.get("messages", [])
        
        # Prepend the memory context
        kwargs["messages"] = [system_msg] + messages
        return kwargs

    def extract_response(self, response: Any) -> str:
        try:
            return response.choices[0].message.content
        except Exception:
            return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode: str = "silent", model_context_limit: int = 4096, strict: bool = False, model_strength: str = "STRONG"):
        original_create = agent.chat.completions.create
        
        def new_create(*args, **kwargs):
            try:
                # 1. Retrieve
                query = ""
                messages = kwargs.get("messages", [])
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'get') and last_msg.get("role") == "user":
                        query = last_msg.get("content", "")
                        
                memories = retrieve_fn(query) if query else []
                
                # 2. Inject
                new_kwargs = self.inject_memory(kwargs.copy(), memories, strict=strict)
                
                # 3. Target Call
                res = original_create(*args, **new_kwargs)
                
                # 4. Expose Visibility (Hook)
                try:
                    # Attach retrieved memories to the response object for inspection
                    setattr(res, "_nsn_context", memories)
                except: pass
                
                # 5. Log
                log_fn(query, memories, self.extract_response(res))
                
                return res
            except Exception as e:
                logger.error(f"NSN wrapping error for OpenAI: {e}")
                if fallback_mode == "raise": raise
                return original_create(*args, **kwargs)
                
        agent.chat.completions.create = new_create
        return agent
