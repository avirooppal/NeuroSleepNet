# NeuroSleepNet

**Intelligence consolidation for small language models (SLMs).**

NeuroSleepNet (NSN) is a persistent memory layer designed to give SLMs (like Llama 3.2 1b, Phi-3, or Mistral) "long-term memory" that survives process restarts and evolves through sleep cycles.

---

## The 3-Line Magic
Give your AI agent persistent memory with zero overhead.

```python
import nsn

# 1. Zero-config init (auto-detects project & data)
nsn.init(project="my-agent") 

# 2. Wrap any LLM/SLM function
chat = nsn.wrap(your_llm_call)

# 3. Use it! Memory is now persistent and automatic.
chat("Hi, I'm Avi. I like building robots.")
```

---

##  Why NeuroSleepNet?

- **Local-First**: No external vector DB setup required. Uses SQLite + BGE-Small for high-speed local recall.
- **Autonomous Sleep Cycles**: Automatically consolidates episodic memories into semantic knowledge during background "sleep" cycles.
- **Dynamic Governance**: Pin "personality" or "safety" rules that are never forgotten.
- **Developer First**: Includes a powerful CLI and a neural graph dashboard.

---

##  Installation

```bash
pip install neurosleepnet
```

*Note: For local development, we recommend using [uv](https://github.com/astral-sh/uv).*

---

##  CLI Tools

NSN comes with a first-class developer CLI to manage your agent's brain.

```bash
# Launch the visual dashboard
nsn dashboard

# Check memory health and stats
nsn stats

# Search through your agent's memories
nsn memories search "robots"

# Trigger an immediate sleep cycle (consolidation)
nsn sleep
```

---

##  Visual Dashboard
The NSN Dashboard provides a real-time view of your agent's neural pathways.
- **Memory Pulse**: Track which facts are being recalled most.
- **Recall Misses**: Debug why the agent failed to remember specific context.
- **Pathway Map**: Visualize how episodic events consolidate into long-term facts.

---

##  Repository Structure
- `sdk/python/`: The core library and dashboard backend.
- `frontend/`: Source code for the React-based dashboard.
- `examples/`: Reference implementations for agents and bots.
- `distributed/`: Optional components for cloud/multi-container deployments.

---

##  License
MIT License. 
