# NeuroSleepNet Python SDK

A sleep-inspired hybrid memory layer for continual AI learning.

## Installation

```bash
pip install neurosleepnet
```

## Quick Start

```python
from neurosleepnet import NeuroSleepClient

# Initialize client
client = NeuroSleepClient(
    api_key="your_nsn_live_key",
    base_url="http://localhost:8001/api/v1"
)

# 1. Create a task (context)
task = client.create_task("User Profile Learning")
task_id = task["id"]

# 2. Add memories
client.add_memory(
    content="User prefers dark mode and Python as primary language.",
    task_id=task_id,
    metadata={"source": "chat_session_1"}
)

# 3. Search with Attention
results = client.search(
    query="What are the user's preferences?",
    task_id=task_id,
    top_k=3
)

for res in results["memories"]:
    print(f"Memory: {res['content']}")
    print(f"Attention Score: {res['attention_score']}")
    print(f"Reason: {res['why_retrieved']}\n")

# 4. Trigger Sleep Phase (Consolidation)
client.trigger_sleep()
```

## Features

- **Attention-based Retrieval**: Weighted by semantic similarity, recency, and consolidation score.
- **Residual Pathways**: Cross-task context inheritance.
- **Sleep Consolidation**: Nightly or manual memory reinforcement and pruning.
- **Local-first hybrid**: OpenAI primary with local fallback.
