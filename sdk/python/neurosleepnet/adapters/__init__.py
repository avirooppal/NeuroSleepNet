"""
AdapterRegistry — detect which adapter to use for a given agent.

Detection priority follows the architecture spec:
  1. LangChain AgentExecutor (Tier 1)
  2. LCEL / LangGraph (Tier 2/3, detected inside LangChainAdapter)
  3. HuggingFace pipeline
  4. OpenAI-compatible (OpenAI, Groq, Together, Azure, Anyscale)
  5. Anthropic
  6. Ollama
  7. LlamaIndex
  8. Generic (wraps __call__ directly — always matches)
"""
from typing import Any
import logging

from .base import AbstractAdapter
from .langchain import LangChainAdapter
from .huggingface import HuggingFaceAdapter
from .openai_compat import OpenAIAdapter
from .generic import GenericAdapter

logger = logging.getLogger(__name__)

# Lazy-load optional adapters to avoid import errors when deps aren't installed
def _try_import_anthropic():
    try:
        from .anthropic import AnthropicAdapter
        return AnthropicAdapter
    except ImportError:
        return None

def _try_import_ollama():
    try:
        from .ollama import OllamaAdapter
        return OllamaAdapter
    except ImportError:
        return None

def _try_import_llama_index():
    try:
        from .llama_index import LlamaIndexAdapter
        return LlamaIndexAdapter
    except ImportError:
        return None


class AdapterRegistry:

    @classmethod
    def detect(cls, agent: Any) -> AbstractAdapter:
        """
        Detect the appropriate adapter for the given agent.
        Priority order matches the architecture spec exactly.
        """
        # LangChain — handles Tier 1 (AgentExecutor), Tier 2 (LCEL), Tier 3 (LangGraph)
        if LangChainAdapter.detect(agent):
            logger.debug("Detected adapter: LangChainAdapter (routing to Tier 1/2/3)")
            return LangChainAdapter()

        # HuggingFace pipeline
        if HuggingFaceAdapter.detect(agent):
            logger.debug("Detected adapter: HuggingFaceAdapter")
            return HuggingFaceAdapter()

        # OpenAI-compatible (OpenAI, Groq, Together, Azure, Anyscale)
        if OpenAIAdapter.detect(agent):
            logger.debug("Detected adapter: OpenAIAdapter")
            return OpenAIAdapter()

        # Anthropic
        AnthropicAdapter = _try_import_anthropic()
        if AnthropicAdapter and AnthropicAdapter.detect(agent):
            logger.debug("Detected adapter: AnthropicAdapter")
            return AnthropicAdapter()

        # Ollama
        OllamaAdapter = _try_import_ollama()
        if OllamaAdapter and OllamaAdapter.detect(agent):
            logger.debug("Detected adapter: OllamaAdapter")
            return OllamaAdapter()

        # LlamaIndex
        LlamaIndexAdapter = _try_import_llama_index()
        if LlamaIndexAdapter and LlamaIndexAdapter.detect(agent):
            logger.debug("Detected adapter: LlamaIndexAdapter")
            return LlamaIndexAdapter()

        # Generic fallback — wraps __call__ directly
        logger.debug("Detected adapter: GenericAdapter (fallback)")
        return GenericAdapter()


def get_adapter(agent: Any) -> AbstractAdapter:
    return AdapterRegistry.detect(agent)
