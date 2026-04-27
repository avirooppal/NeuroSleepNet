# NeuroSleepNet

**Persistent memory for AI agents. Drop-in. Open-source. Fully Local.**

NeuroSleepNet gives your local LLMs and agents a biologically-inspired long-term memory layer. It eliminates "context-window amnesia" by automatically storing, retrieving, and consolidating memories in the background.

---

## Quick Start

```bash
pip install neurosleepnet
```

```python
import neurosleepnet as nsn

# Zero-config initialization for local use
nsn.init(project="my-agent-demo")

# Drop-in wrap for OpenAI, LangChain, HuggingFace, etc.
agent = nsn.wrap(your_agent)

# Your agent now remembers everything across sessions
response = agent("What was my name again?")
```

### Run the Backend Locally

NeuroSleepNet is designed to be self-hosted. Start the full stack (Vector DB, Redis, API, Dashboard) with one command:

```bash
docker compose up -d
```

---

## Why NeuroSleepNet?

- **Biologically Inspired**: Implements a "Sleep Engine" that reinforces important memories and prunes irrelevant ones, just like the human brain.
- **Local-First**: No API keys, no cloud lock-in. Your data stays on your infrastructure.
- **Transparent Proxy**: Wrap your existing LLM clients or agents. `isinstance()` checks and attributes are preserved.
- **Attention-based Retrieval**: Hybrid scoring using semantic similarity, recency, and consolidation strength.
- **Offline Resilience**: Built-in SQLite cache means your agent keeps working even if the backend is temporarily unreachable.

---

## Features

- **Semantic Memory**: High-dimensional vector search for relevant context.
- **Sleep Consolidation**: Automated background tasks for memory "dreaming" (reinforcement).
- **Encryption at Rest**: All memories are AES-256 encrypted by default.
- **PII Redaction**: Automatically scrubs sensitive data (emails, SSNs) before storage.
- **Interactive Dashboard**: Explore memories, visualize the "Memory Pulse" graph, and debug retrieval in real-time.

---

## Framework Support

| Framework | Status |
|---|---|
| LangChain (`AgentExecutor`, LCEL) | ✅ Native Support |
| OpenAI SDK | ✅ Native Support |
| HuggingFace `pipeline` | ✅ Native Support |
| Anthropic / Claude | ✅ Native Support |
| Ollama / Custom Callables | ✅ Native Support |

---

## Local Development

```bash
# Install dependencies
uv sync

# Run the backend (FastAPI)
cd backend && uv run uvicorn app.main:app --reload

# Start workers for memory consolidation
uv run celery -A app.workers.tasks worker -Q sleep --loglevel=info

# Run the frontend (React)
cd frontend && npm run dev
```

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
