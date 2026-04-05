# NeuroSleepNet Node.js SDK

A sleep-inspired hybrid memory layer for continual AI learning.

## Installation

```bash
npm install @neurosleepnet/sdk
```

## Quick Start

```javascript
const { NeuroSleepClient } = require("@neurosleepnet/sdk");

const client = new NeuroSleepClient("your_nsn_live_key");

async function main() {
  // 1. Create a task (context)
  const task = await client.createTask("User Profile Learning");
  const taskId = task.id;

  // 2. Add memories
  await client.addMemory(
    "User prefers dark mode and Node.js for backend development.",
    taskId,
    { source: "chat_session_1" }
  );

  // 3. Search with Attention
  const response = await client.search("What are the user's preferences?", taskId);

  for (const res of response.memories) {
    console.log(`Memory: ${res.content}`);
    console.log(`Attention Score: ${res.attention_score}`);
    console.log(`Reason: ${res.why_retrieved}\n`);
  }

  // 4. Trigger Sleep Phase (Consolidation)
  await client.triggerSleep();
}

main();
```

## Features

- **Attention-based Retrieval**: Weighted by semantic similarity, recency, and consolidation score.
- **Residual Pathways**: Cross-task context inheritance.
- **Sleep Consolidation**: Nightly or manual memory reinforcement and pruning.
- **Local-first hybrid**: OpenAI primary with local fallback.
