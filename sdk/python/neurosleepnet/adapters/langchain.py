from typing import Any, List, Dict
from .base import AbstractAdapter, enforce_context_bounds
import logging

try:
    from langchain.callbacks.base import BaseCallbackHandler
    has_langchain = True
except ImportError:
    has_langchain = False
    
logger = logging.getLogger(__name__)

class NSNCallbackHandler:
    """Mock fallback if real langchain isn't present"""
    pass

if has_langchain:
    class NSNCallbackHandler(BaseCallbackHandler):
        def __init__(self, log_fn):
            self.log_fn = log_fn
            
        def on_tool_end(self, output: str, **kwargs: Any) -> None:
            """Snoop intermediate tool executions as memory thoughts"""
            try:
                self.log_fn("", [], f"Tool Observation: {output}")
            except Exception:
                pass

class LangChainAdapter(AbstractAdapter):
    @classmethod
    def detect(cls, agent: Any) -> bool:
        module_name = getattr(agent.__class__, '__module__', '')
        return "langchain" in module_name.lower() or hasattr(agent, "invoke")

    def inject_memory(self, kwargs: Dict[str, Any], memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        return kwargs

    def extract_response(self, response: Any) -> str:
        if hasattr(response, "content"):
            return response.content
        return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode: str = "silent", model_context_limit: int = 4096):
        if not hasattr(agent, "invoke"):
            return agent

        original_invoke = agent.invoke
        
        def new_invoke(input_data, config=None, **kwargs):
            try:
                query = str(input_data)
                if isinstance(input_data, dict) and "input" in input_data:
                    query = str(input_data["input"])

                memories = retrieve_fn(query) if query else []
                memories = enforce_context_bounds(query, memories, model_context_limit)
                
                # Prepend to string input
                if isinstance(input_data, str) and memories:
                    context = " ".join([m.get("content", "") for m in memories])
                    input_data = f"Context: {context}\n\nQuery: {input_data}"
                elif isinstance(input_data, dict) and "input" in input_data and memories:
                    context = " ".join([m.get("content", "") for m in memories])
                    input_data["input"] = f"Context: {context}\n\nQuery: {input_data['input']}"
                
                # Inject trace hooks
                if has_langchain:
                    cb = NSNCallbackHandler(log_fn)
                    if config is None:
                        config = {"callbacks": [cb]}
                    else:
                        if "callbacks" in config:
                            config["callbacks"].append(cb)
                        else:
                            config["callbacks"] = [cb]
                            
                res = original_invoke(input_data, config=config, **kwargs)
                log_fn(query, memories, self.extract_response(res))
                return res
            except Exception as e:
                logger.error(f"NSN wrapping error for LangChain: {e}")
                if fallback_mode == "raise": raise
                return original_invoke(input_data, config=config, **kwargs)
                
        agent.invoke = new_invoke
        return agent
