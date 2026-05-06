# NeuroSleepNet (NSN)

**The Adaptive Memory Layer for AI Agents.**

NeuroSleepNet (NSN) is a local-first, production-ready memory library that gives Large Language Models (LLMs) and Small Language Models (SLMs) a persistent "brain." It automatically manages the lifecycle of memories—from initial observation to long-term consolidation—all with zero external dependencies.

---

## 🚀 V2: The Synthetic Reasoning Engine
NeuroSleepNet V2 introduces the **Synthetic Reasoning Engine**, a major architectural upgrade that enables agents to perform cognitive memory synthesis:
- **Cognitive Synthesis**: Automatically clusters related episodic memories and synthesizes them into "Golden Facts."
- **Precision Re-ranking**: Implements a Stage 2 re-ranking pipeline for ultra-high precision retrieval.
- **Graph-RAG Foundation**: Enables structural memory relationships via a built-in Graph linking layer.

---

## ⚡ The 3-Line Magic (Zero-Config)
NSN is designed to be plug-and-play. It automatically detects your model's strength and adapts its retrieval strategy.

```python
import nsn

# 1. Wrap any LLM/SLM function (OpenAI, LangChain, or custom)
# NSN auto-detects model limits and sets optimal thresholds.
agent = nsn.wrap(your_model_call)

# 2. Use it. Memory is now persistent and automatic.
agent("Hi, I'm Ava. I'm a robotics engineer from Toronto.")

# 3. Next session, it remembers.
agent("What was my name and city?")
```

---

## 🧠 Adaptive Intelligence
NSN is "Model-Aware." It uses a built-in registry to apply **Best Known Configurations** based on the model you wrap:

| Model Strength | Example Models | Auto-Threshold | Context Window |
| :--- | :--- | :--- | :--- |
| **SLM (Weak)** | TinyLlama, Phi-3-mini, SmolLM | `0.32` (Lenient) | `1024` tokens |
| **LLM (Strong)** | GPT-4o, Llama-3.1, Claude-3 | `0.55` (Strict) | `4096` tokens |

---

## 🛠 API Reference

### `nsn.init(...)`
While optional (NSN auto-initializes if skipped), `init` allows you to tune the persistence layer.

```python
nsn.init(
    project="my-agent",             # Partition memories by project
    synthesis_mode=True,            # Enable V2 Cognitive Synthesis
    recall_threshold=None,          # Manual similarity override (0.0 - 1.0)
    memory_window=4096,             # Max tokens to inject into prompts
    sleep_interval=300,             # Background consolidation interval (seconds)
    debug=True                      # See retrieval scores in console
)
```

### `nsn.wrap(fn, ...)`
The primary entry point. Wraps any function `fn(prompt: str) -> str` or `fn(messages: list) -> str`.

- **Automatic Injection**: Retrieves memories and injects them as Markdown or XML context.
- **Stage 2 Re-ranking**: Applies high-precision re-scoring to candidate memories.
- **Automatic Storage**: Saves the user query and agent response as a new episodic memory.

---

## 😴 The Sleep Engine (Memory Evolution)
NSN mimics human memory cycles through background consolidation.

1.  **Episodic Memory**: Raw interactions are stored as "Episodic."
2.  **Consolidation**: During "Sleep" cycles, frequently accessed memories are boosted.
3.  **Synthesis (V2)**: Related episodic fragments are merged into stable **Semantic Knowledge**.
4.  **Decay/Archive**: Memories that are never accessed or contradicted are eventually moved to the archive.

---

## 📊 Visual Dashboard
Monitor your agent's brain in real-time.
```bash
nsn dashboard
```
- **Memory Pulse**: Heatmap of recalled facts.
- **Pathway Map**: Visualize the evolution from episodic chat lines to semantic facts.

---

## 🏗 Repository Structure
- `sdk/python/`: The core library and adaptive engine.
- `benchmarks/`: Performance and retention evaluation suites.
- `frontend/`: The React-based visualization dashboard.

---

## 📄 License
MIT License. Built for the developer community by the NeuroSleepNet team.
