from typing import Any, List, Dict
from .base import AbstractAdapter
import logging

logger = logging.getLogger(__name__)

class OpenAIAdapter(AbstractAdapter):
    @classmethod
    def detect(cls, agent: Any) -> bool:
        # Detect if it's an OpenAI client instance or a completions class
        cls_name = agent.__class__.__name__
        module_name = agent.__class__.__module__
        return "openai" in module_name.lower() or cls_name == "OpenAI"

    def inject_memory(self, kwargs: Dict[str, Any], memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Injects memories as a system message.
        """
        if not memories:
            return kwargs
            
        context_lines = ["[NeuroSleepNet Context — Top relevant memories]"]
        for i, m in enumerate(memories):
            relevance = m.get('score', 0.99)
            date_str = m.get('timestamp', 'recently')
            context_lines.append(f"{i+1}. (score: {relevance:.2f}) {m.get('content')} [{date_str}]")
        context_lines.append("[End of injected context]")
        
        system_content = "\n".join(context_lines)
        system_msg = {"role": "system", "content": system_content}
        
        messages = kwargs.get("messages", [])
        
        # If there's already a system message, we could append to it. 
        # For simplicity, we prepend a new system message to the message list.
        kwargs["messages"] = [system_msg] + messages
        return kwargs

    def extract_response(self, response: Any) -> str:
        try:
            return response.choices[0].message.content
        except Exception:
            return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode: str = "silent", model_context_limit: int = 4096):
        original_create = agent.chat.completions.create
        
        def new_create(*args, **kwargs):
            try:
                # 1. Retrieve
                # Extract the last user message as the query
                query = ""
                messages = kwargs.get("messages", [])
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'get') and last_msg.get("role") == "user":
                        query = last_msg.get("content", "")
                        
                memories = retrieve_fn(query) if query else []
                
                # 2. Inject
                new_kwargs = self.inject_memory(kwargs.copy(), memories)
                
                # 3. Target Call
                res = original_create(*args, **new_kwargs)
                
                # 4. Log
                log_fn(query, memories, self.extract_response(res))
                
                return res
            except Exception as e:
                logger.error(f"NSN wrapping error for OpenAI: {e}")
                if fallback_mode == "raise": raise
                return original_create(*args, **kwargs)
                
        agent.chat.completions.create = new_create
        return agent
