# NeuroSleepNet — Vibe Coding Plan
### The Memory Layer for AI Agents | MVP Integration Build

> **One-liner:** Drop NeuroSleepNet into any AI agent in 3 lines of code.
> It handles the rest — your agent stops forgetting.

---

## 🎯 What We're Building (The Elevator Pitch)

AI agents forget. Every time you update them, retrain them, or switch tasks — they lose what they knew.
NeuroSleepNet is a **plug-in middleware layer** that sits between your agent and its tasks.
It gives any AI agent a **persistent, evolving memory** — without touching the base model.

```python
# Before NeuroSleepNet — your agent forgets
agent.learn(task_b)  # 💀 task_a knowledge gone

# After NeuroSleepNet — 3-line integration
from neurosleepnet import wrap
agent = wrap(agent)
agent.learn(task_b)  # ✅ task_a still intact
```

---

## 🗓️ Build Phases — Vibe Code Edition

> Each phase is self-contained, shippable, and demo-able.
> Stack: **Python · FastAPI · React · PostgreSQL · Redis · Docker**

---

## Phase 0 — Foundation (Week 1–2)
### `The Skeleton`

> Goal: Repo is clean, runs locally, has a live demo endpoint.

**What to build:**
- [ ] Monorepo scaffold: `/core`, `/api`, `/dashboard`, `/examples`
- [ ] `NSNLayer` base class — wraps any callable model
- [ ] In-memory replay buffer (Python dict, no DB yet)
- [ ] Dummy sleep phase: logs "sleep triggered" every N steps
- [ ] FastAPI server with `/learn`, `/predict`, `/sleep` endpoints
- [ ] Docker Compose: app + Redis

**Done when:**
```bash
docker compose up
curl -X POST /learn -d '{"task_id": "t1", "input": [...], "label": [...]}'
curl -X POST /predict -d '{"input": [...]}'
# → returns prediction, no crash
```

**Files to create:**
```
neurosleepnet/
├── __init__.py
├── layer.py          # NSNLayer class
├── buffer.py         # ReplayBuffer
├── sleep.py          # SleepScheduler
├── attention.py      # TaskAttention (stub)
└── residual.py       # ResidualPathway (stub)
api/
├── main.py           # FastAPI app
├── routes.py
docker-compose.yml
```

---

## Phase 1 — Core Memory Engine (Week 2–4)
### `The Brain`

> Goal: Real continual learning works. Forgetting is measurably reduced.

**What to build:**

### 1.1 Latent Replay Buffer
```python
class ReplayBuffer:
    def store(self, task_id: str, embedding: np.ndarray, label: any)
    def sample(self, n: int, strategy="importance") -> List[Memory]
    def score(self, embedding: np.ndarray) -> float  # novelty score
```
- Store compressed latent vectors (not raw data) → privacy-safe, tiny footprint
- Importance scoring: high novelty = stored, low novelty = discarded
- Backend: **Redis** for speed, **PostgreSQL** for persistence

### 1.2 Sleep Phase Engine
```python
class SleepScheduler:
    def should_sleep(self, step: int, task_id: str) -> bool
    def run_sleep(self, model, buffer: ReplayBuffer) -> SleepReport
    def get_report(self) -> dict  # metrics on what was replayed
```
- Triggers on task switch OR every N steps (configurable)
- Replays top-K memories by importance score
- Returns a `SleepReport`: tasks consolidated, forgetting risk delta

### 1.3 Task-Aware Attention (Lightweight Version)
```python
class TaskAttention:
    def encode_task(self, task_id: str) -> np.ndarray
    def gate(self, embedding: np.ndarray, task_ctx: np.ndarray) -> np.ndarray
```
- Simple learned task embedding (no transformer needed at this stage)
- Gates what the model pays attention to per task
- Prevents cross-task interference at the embedding level

### 1.4 Residual Memory Hooks
- Wrap model forward pass with residual skip connections
- Compatible with: PyTorch nn.Module, HuggingFace models, sklearn-style .fit()/.predict()

**Done when:**
- Run on Split-MNIST benchmark
- Accuracy on Task 1 after learning Task 5 > 85% (vs ~19% without NSN)
- Forgetting score displayed in terminal after each sleep phase

---

## Phase 2 — Integration Layer (Week 4–6)
### `The Plug`

> Goal: Any developer can wrap their agent in 5 minutes. No PhD required.

**What to build:**

### 2.1 Universal Wrap API
```python
# Works with anything
from neurosleepnet import wrap

# Wrap a HuggingFace model
model = wrap(AutoModel.from_pretrained("bert-base"))

# Wrap a LangChain agent
agent = wrap(langchain_agent, mode="llm-sidecar")

# Wrap a custom class (just needs .predict())
agent = wrap(MyCustomAgent(), task_boundary="auto")
```

### 2.2 LLM Sidecar Mode
- For frozen LLMs (GPT-4, Claude, Llama) that can't be fine-tuned
- NSN intercepts embeddings and injects task memory as **soft-prompt prefix**
- No base model weights touched — works via API calls
```python
agent = wrap(openai_client, mode="sidecar", inject="soft-prompt")
agent.learn(task_id="support-v2", examples=few_shot_examples)
agent.predict("how do I reset my password?")
# → uses memory of support-v2 context, not generic GPT knowledge
```

### 2.3 Auto Task Boundary Detection
```python
# Don't know when tasks change? NSN figures it out.
agent = wrap(model, task_boundary="auto")
# Internally: monitors embedding distribution shift + gradient spikes
# Fires sleep phase automatically when distribution shift detected
```

### 2.4 Python SDK Packaging
```bash
pip install neurosleepnet
```
- Full type hints, docstrings, changelog
- Publish to PyPI
- README with 3 working examples: PyTorch, HuggingFace, LangChain

**Done when:**
- 3 integration examples run end-to-end from pip install
- LLM sidecar demo works with OpenAI API key
- Auto boundary detection tested on streaming data

---

## Phase 3 — Dashboard + Observability (Week 6–8)
### `The Window`

> Goal: Non-technical stakeholders (PMs, investors) can SEE the memory working.

**What to build:**

### 3.1 Memory Health Dashboard (React)
```
┌─────────────────────────────────────────────────────────┐
│  NeuroSleepNet Dashboard                    🟢 Healthy  │
├───────────────┬─────────────────────────────────────────┤
│ Memory Health │  ████████████████░░  84%                │
│ Tasks Loaded  │  7 tasks active                         │
│ Last Sleep    │  2 min ago · 312 memories replayed      │
│ Forgetting    │  ↓ 0.03  (risk: LOW)                    │
├───────────────┴─────────────────────────────────────────┤
│ Task Performance Over Time                              │
│  t1 ─────────────────────── 91% ✅                     │
│  t2 ──────────────────────── 88% ✅                    │
│  t3 ─────────────────────── 79% ⚠️                     │
│  t4 (active) ████████████── 95% ✅                     │
├─────────────────────────────────────────────────────────┤
│ [Trigger Sleep Now]  [View Replay Log]  [Export Report] │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Forgetting Risk Alert System
- Webhook alerts when forgetting risk exceeds threshold
- Slack / email / PagerDuty integrations
- Auto-triggers emergency sleep phase if risk > critical threshold

### 3.3 REST + WebSocket API
```
GET  /api/health              → memory health score
GET  /api/tasks               → all tasks + per-task accuracy
POST /api/sleep               → manually trigger sleep phase
GET  /api/sleep/report        → last sleep report
WS   /ws/live                 → real-time forgetting risk stream
```

**Done when:**
- Dashboard live at localhost:3000
- Forgetting risk updates in real time during a demo
- "Trigger Sleep Now" button visibly recovers performance on screen

---

## Phase 4 — Demo Day Build (Week 8–10)
### `The Story`

> Goal: One killer demo that makes developers want it and investors fund it.

**The Demo Script (10 minutes):**

1. **"The Problem" (2 min)** — Live-code a simple agent, train on Task A (sentiment), train on Task B (translation) → show Task A accuracy crash from 94% → 21%

2. **"The Fix" (1 min)** — Add 3 lines: `from neurosleepnet import wrap` + `agent = wrap(agent)`

3. **"Same Training" (2 min)** — Repeat exact same training. Dashboard opens. Replay buffer filling. Sleep phase triggers.

4. **"The Result" (2 min)** — Task A accuracy: 91%. Task B accuracy: 93%. Both. Simultaneously.

5. **"It Works With Yours" (3 min)** — Live swap in a LangChain agent, a HuggingFace BERT, show same 3-line integration works

**Demo repo:** `github.com/neurosleepnet/demo` — one-click Colab notebook

---

## 🧱 Tech Stack Decisions

| Layer | Choice | Why |
|---|---|---|
| Core ML | PyTorch | Most widely used, easiest to hook |
| Replay Store | Redis + Postgres | Redis = fast sampling, Postgres = persistence |
| API | FastAPI | Async, auto-docs, fastest to vibe code |
| Dashboard | React + Recharts | Fast to build, clean charts |
| Packaging | Python SDK on PyPI | Lowest friction adoption |
| Deployment | Docker + Railway/Render | One-click cloud deploy for demos |
| LLM Compat | OpenAI SDK + HuggingFace | Covers 90% of target users |

---

## 📦 Deliverables Per Phase

| Phase | Deliverable | Demo-able? |
|---|---|---|
| 0 | Running API skeleton | ✅ curl demo |
| 1 | Core memory engine | ✅ terminal benchmark |
| 2 | SDK + 3 integrations | ✅ pip install demo |
| 3 | Live dashboard | ✅ visual demo |
| 4 | Full story demo | ✅ investor/dev pitch |

---

## 🚀 How to Show This to Different Audiences

### For Developers
> Show Phase 2. Open terminal. `pip install neurosleepnet`. Wrap their own model live.
> Message: *"It takes 3 lines. You don't need to understand the internals."*

### For Companies / Enterprise
> Show Phase 3. Open dashboard. Show forgetting risk score.
> Message: *"You can see your AI's memory health the same way you monitor uptime. And fix it."*

### For Investors
> Run the full Phase 4 demo. Before vs. after. Numbers on screen.
> Message: *"Every production AI system has this problem. We're the first plug-in layer that solves it without retraining."*

---

## ⚡ Vibe Coding Rules for This Project

1. **Ship phases, not features** — each phase runs independently
2. **Stubs are fine** — Phase 0 attention module is a pass-through, that's ok
3. **Benchmark first** — Split-MNIST is your ground truth, run it after every commit
4. **Dashboard is not optional** — visual proof > terminal logs for non-technical audiences
5. **3-line rule** — if integration takes more than 3 lines, redesign the API
6. **README-driven development** — write the README for each phase before the code
7. **One Colab notebook per phase** — zero-install proof that it works

---

## 🔑 The 3 Numbers That Matter

| Metric | Target | Why It Matters |
|---|---|---|
| Integration time | < 5 minutes | Developer adoption speed |
| Forgetting reduction | > 70% vs baseline | Core technical proof |
| Sleep overhead | < 15% compute | Production viability |

---

## 📁 Final Repo Structure (End State)

```
neurosleepnet/
├── core/
│   ├── layer.py           # NSNLayer — the main wrapper
│   ├── buffer.py          # ReplayBuffer
│   ├── sleep.py           # SleepScheduler
│   ├── attention.py       # TaskAttention
│   └── residual.py        # ResidualPathways
├── api/
│   ├── main.py            # FastAPI app
│   └── routes.py
├── dashboard/
│   ├── src/App.jsx
│   └── src/components/    # MemoryHealth, TaskChart, SleepLog
├── examples/
│   ├── pytorch_example.py
│   ├── huggingface_example.py
│   ├── langchain_example.py
│   └── demo_notebook.ipynb
├── benchmarks/
│   └── split_mnist.py
├── docker-compose.yml
├── pyproject.toml
└── README.md              # The 3-line integration hero shot
```

---

*NeuroSleepNet · v0.1 · Build Plan · March 2026*
*"Your agent should remember everything it learned. Now it can."*
