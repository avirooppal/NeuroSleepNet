# NeuroSleepNet

**The Memory Layer for AI Agents**

Drop NeuroSleepNet into any AI agent in 3 lines of code. It handles the rest — your agent stops forgetting.

## Get Started

```bash
pip install neurosleepnet
```

```python
# Before NeuroSleepNet — your agent forgets
agent.learn(task_b)  # 💀 task_a knowledge gone

# After NeuroSleepNet — 3-line integration
from neurosleepnet import wrap
agent = wrap(agent)
agent.learn(task_b)  # ✅ task_a still intact
```

## Features
- **Plug-and-play**: Works with PyTorch, HuggingFace, LangChain, or any callable python class.
- **Latent Replay Buffer**: Stores highly compressed memory embeddings, not raw data.
- **LLM Sidecar Mode**: Injects task-relevant memory dynamically for frozen LLMs (GPT-4, Claude).
- **Auto Task Boundary Detection**: Knows when your data distribution shifts.
- **Dashboard**: Real-time memory health and forgetting risk monitoring.

## Run Locally (API & Dashboard)
```bash
docker compose up
```
Dashboard available at `http://localhost:3000`.
