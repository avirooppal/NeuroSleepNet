from typing import Any
import logging

from .base import AbstractAdapter
from .openai_compat import OpenAIAdapter
from .langchain import LangChainAdapter
from .huggingface import HuggingFaceAdapter
from .generic import GenericAdapter

logger = logging.getLogger(__name__)

class AdapterRegistry:
    _adapters = [
        OpenAIAdapter,
        LangChainAdapter,
        HuggingFaceAdapter,
        # Other adapters like Ollama, Anthropic would go here.
        GenericAdapter # Must be last as fallback
    ]

    @classmethod
    def detect(cls, agent: Any) -> AbstractAdapter:
        for adapter_cls in cls._adapters:
            # We instantiate adapter immediately for simplicity, could also just return class and instantiate later
            if adapter_cls.detect(agent):
                logger.debug(f"Detected adapter: {adapter_cls.__name__}")
                return adapter_cls()
                
        # Fallback (should ideally never hit because GenericAdapter detects all callables)
        return GenericAdapter()

def get_adapter(agent: Any) -> AbstractAdapter:
    return AdapterRegistry.detect(agent)
