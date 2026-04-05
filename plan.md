# NeuroSleepNet — Master Implementation Plan
### *Persistent, Bio-inspired Memory for AI Agents*

---

## 1. The Core Vision
NeuroSleepNet is a **persistent, self-consolidating memory middleware** for LLM apps. It sits between your app and your LLM to handle storage, consolidation, retrieval, and interference prevention.

### Problem We're Solving
- **Facts vs Context**: Existing memory layers store facts but forget *why* and *when*.
- **Silent Degradation**: Older memories get buried without signal.
- **Interference**: Retrieved memories from Task A bleed into Task B.

---

## 2. Hybrid Architecture (Two-Tier)

### Technology Stack
| Layer | Choice | Reason |
|---|---|---|
| **API** | FastAPI | Fast, async-first, auto-generated OpenAPI docs. |
| **AI Layer** | **Hybrid Provider** | **OpenAI** (Paid) with **FastEmbed** (Local fallback) for zero-cost operation. |
| **Job Runner** | **APScheduler** | Robust task scheduling for consolidation jobs. |
| **Database** | SQLite + `GraphStore` | Zero-infra to start. |
| **Safety** | **SafetyEngine** | PII scrubbing, injection detection, and quota guard. |

### Core Modules
1. **`ingestion.py`**: Chunks messages and sanitizes content.
2. **`embedding_provider.py`**: Dynamic fallback between local ONNX and OpenAI.
3. **`safety_engine.py`**: Guardrails and role-based quotas.
4. **`task_detector.py`**: High-precision context switching.
5. **`consolidation.py`**: The "Sleep Engine." Async job to merge/decay nodes.

---

## 3. Developer SDK
### Quickstart (Python)
```python
from neurosleepnet import NeuroSleepClient
memory = NeuroSleepClient(base_url="http://localhost:8000")

# Register with PII scrubbing
memory.write_memory(user_id="u1", session_id="s1", messages=messages, scrub_pii=True)

# Retrieve relevant context
context = memory.read_memory(user_id="u1", query="Search query")
```

---

## 4. Admin & User Portals (Mem0-Inspired)
Built with **Next.js 14**, the portal provides a search-first observability interface.

### Pricing Tiers (v4)
| Tier | Price | Included | Feature Set |
|---|---|---|---|
| **Standard** | **Free** | 1,000 nodes | Local embeddings, PII scrubbing. |
| **Growth** | **$29/mo** | 100,000 nodes | OpenAI embeddings, Priority Recall. |

### Key Features
- **Memory Command Center**: CMD+K search-first interface for auditing long-term memory.
- **Activity Feed**: Real-time audit logs of all memory ingestions and retrievals.
- **Safety Dashboard**: View and manage PII scrubbing rules and security logs.

---

## 5. Definition of Done (Plug & Play)
- [x] **Hybrid AI**: Auto-fallback to local models if API key is missing.
- [x] **Safety**: PII scrubbing and injection guards active.
- [x] **UI**: Search-first "Mem0-style" dashboard.
- [x] **Installer**: One-click `install.py` for zero-config setup.