# NeuroSleepNet: Final Project Overview

## 🎯 The Vision
**NeuroSleepNet** is the definitive "Memory Layer for AI Agents" aiming to solve catastrophic forgetting inside Language Models. It focuses on **Zero-Friction Developer Experience**—giving any AI application continuous, infinite memory with just two lines of code (`nsn.init()` and `nsn.wrap()`).

It mimics human memory constraints: saving useful information dynamically, selectively retrieving it using psychological biases (recency, frequency, consolidation context), and executing a backend "Sleep Phase" to prune useless knowledge.

---

## 🛠️ The Technology Stack

NeuroSleepNet is a full-stack, distributed platform with an embedded SDK architecture designed to work in any environment, from heavy cloud servers to fully disconnected local machines.

### 1. The Core Application / Backend
- **Framework:** Python (FastAPI) for high-performance async API routes.
- **Database:** PostgreSQL extended with `pgvector` for storing and performing rapid similarity searches on high-dimensional vectors.
- **ORM & Data Access:** SQLAlchemy with `asyncpg` for asynchronous database interactions.
- **Microservices:**
  - `nsn-embed`: A standalone microservice using `fastembed` for blazing fast embedding generation, keeping API latency ultra-low.
- **Asynchronous Task Engine (Sleep Engine):** Celery backed by Redis Streams, allowing robust message brokering and background database rollups during the simulated "Sleep Phase".

### 2. The Python SDK (`neurosleepnet`)
- **Universal Adapter Protocol:** The SDK automatically detects the agent type and binds to its logic. Explicitly supports:
  - HuggingFace Models (`transformers.pipeline`)
  - OpenAI (and APIs utilizing OpenAI's client compat)
  - LangChain
  - Generic Python Callables
- **Offline SQLite Cache:** `cache.py` allows the memory layer to function 100% offline using an embedded local SQLite fallback. No vector database is required for local integration or testing!
- **Zero-Config Wrapping:** Simply dropping `wrapped_model = nsn.wrap(model)` handles embedding generation, storage, indexing, and runtime context-injection automatically.

### 3. The Trust Engine (Benchmarking & Analytics)
- **`nsn-bench` CLI:** A built-in testing pipeline designed to prove SLM (Small Language Model) amplification.
- **Five Core Scenarios:** Evaluates models out-of-the-box on:
  - Multi-Turn Recall
  - Cross-Session Memory
  - Catastrophic Forgetting Resistance
  - Small Model Amplification
  - Attention Precision@5
- **Dual-Mode Reporting:** Capable of rendering rich ASCII terminal visualizations and generating fully standalone, distributable HTML Dashboard mockups. It hooks directly to the backend to mint SVG Badges for repositories.

### 4. The Frontend Platform
- **Dashboard Stack:** React 18 / TypeScript / Vite.
- **Styling:** Tailwind CSS with Radix UI components (shadcn/ui layout approach).
- **Tooling:** Zustand (Global State), React Router, Framer Motion (Animations), Recharts (Analytics logic).

---

## 🧠 How it Works (Core Architecture)

### 1. Memory Ingestion & Agent Integration
When your agent encounters new information, the `nsn.wrap()` function intercepts it inside your main process loop. It saves the context silently via the Python SDK, using a fallback architecture (Async API calls preferred, SQLite local caching if offline).

### 2. Semantic Search & Attention Reranking
During retrieval, NeuroSleepNet doesn't just do normal RAG (Retrieval Augmented Generation). It computes an **Attention Score** based on human psychology:
* `AttentionScore = (CosineSimilarity × 0.5) + (RecencyWeight × 0.2) + (ConsolidationScore × 0.2) + (ImportanceBoost × 0.1)`
This ensures models don't just vomit old search results, they fetch *functionally relevant* facts.

### 3. The Sleep Engine
Nightly routines are processed via Celery background workers. The engine scans the PostgreSQL tables to boost the "Consolidation Score" of frequently accessed memories and systematically drops/archives poorly accessed data.

### 4. Local Model Amplification (SLM Focus)
The platform explicitly shines in the sub-7 Billion parameter LLM market (e.g., `SmolLM`, `TinyLlama`, `Qwen-0.5B`). The wrapper intercepts Chat-Templating dictionaries from HuggingFace Transformers pipelines, forcibly injecting background memory as transient system prompts, dynamically buffing the context window capabilities of tiny edge compute hardware.

---

## 🚀 Deployment Topography

The system uses highly streamlined containerization. Deployment happens via standard `docker-compose up`:
1. `api`: FastAPI backend running Uvicorn on 8000.
2. `embed`: Standalone text embedding container caching BAAI/bge models.
3. `worker`: Redis-bound Celery daemon for the sleep engine.
4. `db`: Pgvector accelerated PostgreSQL instance.
5. `redis`: Core queue state cache.
6. `nginx`: A reverse proxy router matching routes to the SPA dashboard and the v1 endpoints.

It's currently optimized for zero dependencies aside from Docker on user hardware. For testing the SDK, the backend is entirely optional via the `OfflineCache` SQLite layer implementation.
