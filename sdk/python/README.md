# NeuroSleepNet Python SDK

A sleep-inspired hybrid memory layer for continual AI learning. Give your local LLMs and agents infinite memory with a single line of code.

## Installation

```bash
pip install neurosleepnet
```

For local LLM support (HuggingFace, Torch):
```bash
pip install "neurosleepnet[local_llm]"
```

## Quick Start

```python
import neurosleepnet as nsn

# 1. Initialize — no API keys required for local use
nsn.init(project="my-agent-v1")

# 2. Wrap your agent (OpenAI, LangChain, HuggingFace, etc.)
# All memory injection and storage becomes transparent.
agent = nsn.wrap(your_agent)

# 3. Use your agent as normal
response = agent("What did we talk about in our last session?")
```

## Core Features

- **Project Scoping**: Isolate memories by project or agent identity.
- **Attention-based Retrieval**: Hybrid semantic search + recency weighting.
- **Sleep Consolidation**: Nightly background pruning and reinforcement of important facts.
- **Local-First**: Built-in SQLite fallback ensures your agent never crashes, even if the backend is down.
- **Zero-Ops**: Designed to run entirely on your own infrastructure.

## Advanced API

```python
# Manually remember a fact
nsn.remember("User prefers Python", importance=0.9, tags=["pref"])

# Retrieve memories semantically
memories = nsn.recall("coding preferences", top_k=3)

# Diagnostics
nsn.status()

# Explain why a memory was retrieved
nsn.explain_last()

# Export/Import full state
state = nsn.snapshot()
nsn.restore(state)
```

## License
Apache 2.0
