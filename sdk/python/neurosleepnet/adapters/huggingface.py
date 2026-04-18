from typing import Any, List, Dict
import logging
from .base import AbstractAdapter, enforce_context_bounds, handle_streaming_response

logger = logging.getLogger(__name__)

class HuggingFaceAdapter(AbstractAdapter):
    @classmethod
    def detect(cls, agent: Any) -> bool:
        # Detect if this is a HuggingFace transformers pipeline
        return agent.__class__.__name__ == "TextGenerationPipeline" or "Pipeline" in agent.__class__.__name__

    def inject_memory(self, *args, memories: List[Dict[str, Any]], **kwargs) -> Any:
        # We don't implement this strictly because wrap_call handles the injection logic
        pass

    def extract_response(self, response: Any) -> str:
        # A pipeline returns a list of dicts: [{'generated_text': '...'}]
        if isinstance(response, list) and len(response) > 0:
            if isinstance(response[0], dict) and "generated_text" in response[0]:
                return response[0]["generated_text"]
        return str(response)

    def wrap_call(self, agent: Any, retrieve_fn, log_fn, fallback_mode: str = "silent", model_context_limit: int = 4096):
        original_call = agent.__call__
        
        def new_call(*args, **kwargs):
            try:
                # pipeline("prompt", max_new_tokens=...)
                if not args and "text_inputs" not in kwargs:
                    return original_call(*args, **kwargs)
                    
                # HF pipelines can take string or list of strings
                prompt = args[0] if args else kwargs.get("text_inputs")
                
                # We specifically handle chat templating: list of dicts [{"role": "user", "content": "..."}]
                is_chat = isinstance(prompt, list) and isinstance(prompt[0], dict) and "role" in prompt[0]
                
                query_str = ""
                if is_chat:
                    query_str = getattr(prompt[-1], "get", lambda x: "")("content")
                elif isinstance(prompt, str):
                    query_str = prompt
                
                memories = retrieve_fn(query_str) if query_str else []
                memories = enforce_context_bounds(query_str, memories, model_context_limit)
                
                if memories:
                    context = " ".join([m.get("content", "") for m in memories])
                    if is_chat:
                        # Find the first system message, or inject one
                        system_idx = next((i for i, msg in enumerate(prompt) if msg.get("role") == "system"), -1)
                        context_msg = f"Relevant background memory: {context}"
                        if system_idx >= 0:
                            prompt[system_idx]["content"] += f"\n\n{context_msg}"
                        else:
                            prompt.insert(0, {"role": "system", "content": context_msg})
                    elif isinstance(prompt, str):
                        # Simple string prepending
                        prompt = f"Relevant background memory: {context}\n\nUser: {prompt}"
                
                # Replace the argument
                if args:
                    args = (prompt,) + args[1:]
                else:
                    kwargs["text_inputs"] = prompt
                
                res = original_call(*args, **kwargs)
                return handle_streaming_response(res, log_fn, query_str, memories, self.extract_response)

            except Exception as e:
                logger.error(f"NSN HuggingFace Pipeline wrapper error: {e}")
                if fallback_mode == "raise": raise
                return original_call(*args, **kwargs)
                
        return new_call
