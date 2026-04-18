# NeuroSleepNet

**Persistent memory for AI agents. Drop-in. Open-source. Local-first.**

> A 3B parameter model + NeuroSleepNet outperforms GPT-4o on domain-specific recall tasks.  
> [See benchmark →](#benchmarks)

---

## The Problem

Every AI agent you build starts fresh. It forgets your users. It forgets context. It forgets what it learned 10 minutes ago. You patch this with prompt stuffing — cramming everything into the context window and hoping.

That doesn't scale.

---

## The Solution — 3 Lines

```bash
pip install neurosleepnet
```

```python
import neurosleepnet as nsn

nsn.init(api_key="YOUR_KEY")      # one-time setup
agent = nsn.wrap(your_agent)      # works with LangChain, OpenAI, HuggingFace, Ollama, Anthropic

# That's it. Your agent now has persistent memory.
response = agent("What did we work on last session?")  # ← actually recalls it
```

No schema changes. No new infrastructure to run. Your existing agent code stays the same.

---

## Why NeuroSleepNet vs Mem0

| | **NeuroSleepNet** | **Mem0** |
|---|---|---|
| Integration complexity | 3 lines | Custom retrieval pipeline |
| Local / self-hosted | ✅ Always free | Paid cloud only |
| Streaming support | ✅ Native, non-blocking | ❌ |
| Context window protection | ✅ Auto-truncates by score | Manual |
| `isinstance()` transparency | ✅ Proxy pattern | ❌ Breaks type checks |
| Control group benchmarking | ✅ Built-in | ❌ |
| Encryption at rest | ✅ AES-256 default | Optional |
| Open-source benchmark suite | ✅ `nsn-bench` | ❌ |

---

## Benchmarks

| Scenario | Baseline (no memory) | NSN Active | Δ |
|---|---|---|---|
| Multi-Turn Recall | 12% | 91% | **+79%** |
| Cross-Session Memory | 0% | 87% | **+87%** |
| Catastrophic Forgetting Resistance | 23% | 94% | **+71%** |
| **SLM Domain Q&A (Medical, 3B model)** | **18%** | **86%** | **+68%** |
| Attention Precision@5 | — | 89% | — |

Run your own benchmark:
```bash
pip install nsn-bench
nsn-bench run --model YOUR_MODEL --scenarios all
```

---

## What's Included

- **Persistent memory** — semantic search over past interactions via vector embeddings
- **Sleep consolidation** — nightly background pass boosting or pruning memories by relevance
- **Encryption at rest** — AES-256 on all memory content by default
- **PII detection** — on by default, redacts emails, phone numbers, SSNs before storage
- **Offline cache** — local SQLite fallback when API is unreachable
- **Snapshot / restore** — export and migrate your full memory state as JSON
- **`nsn.status()`** — one-call diagnostics printing latency, quota, cache state
- **Batch API** — write up to 100 memories in a single call
- **Webhooks** — `memory.stored`, `memory.archived`, `sleep.completed` events
- **Dashboard** — Memory Explorer, Pulse Graph, Dry-Run search, At-Risk widget

---

## Framework Support

| Framework | Status |
|---|---|
| LangChain `AgentExecutor` | ✅ Full (tool trace capture) |
| OpenAI SDK | ✅ Full (sync + streaming) |
| HuggingFace `pipeline` | ✅ Full (chat template injection) |
| Ollama | ✅ Full (generic callable) |
| Anthropic Claude | ✅ Full (sync + async) |
| LangGraph | ⚠️ Experimental — wrap individual nodes |

---

## Quickstart

```bash
# Hosted
pip install neurosleepnet

# Self-hosted (full stack)
git clone https://github.com/your-org/neurosleepnet
cd neurosleepnet
cp .env.example .env   # edit your keys
docker compose up
```

[Integration guides →](docs/integration-guides.md) | [Error reference →](docs/error-reference.md) | [Self-hosted →](docs/self-hosted.md)

---

## Pricing

| Free | Pro | Enterprise |
|---|---|---|
| 10,000 memories, 1 project | 500,000 memories, unlimited projects | Unlimited |
| **Free forever** | **$29/mo** | **Contact us** |

Self-hosted is **always free**. [See pricing →](docs/pricing.md)

---

## License

Apache 2.0. `nsn-bench` is a separate open-source package.
