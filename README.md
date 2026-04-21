# NeuroSleepNet — Developer Documentation

**Persistent memory for AI agents. Drop-in. Open-source. Local-first.**

A production-ready memory layer platform designed to give AI agents infinite, persistent context through semantic search, intelligent consolidation, and local-first architecture.

**Table of Contents**
- [Quick Start](#quick-start)
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Running the Application](#running-the-application)
- [SDK Usage](#sdk-usage)
- [API Documentation](#api-documentation)
- [Testing & Benchmarking](#testing--benchmarking)
- [Deployment](#deployment)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Quick Start

### For SDK Users (Integration Only)

```bash
pip install neurosleepnet
```

```python
import neurosleepnet as nsn

nsn.init(api_key="YOUR_KEY")
agent = nsn.wrap(your_agent)

response = agent("What did we work on last session?")
```

### For Full Development (Backend + Frontend + Services)

```bash
# Clone and setup
git clone https://github.com/avirooppal/NeuroSleepNet.git
cd NeuroSleepNet

# Using Docker (recommended)
docker-compose up -d

# Or manual setup (see Installation section)
```

Then visit `http://localhost:3000` for the dashboard and `http://localhost:8000/docs` for API docs.

---

## Project Overview

**NeuroSleepNet** solves catastrophic forgetting in AI systems through:

- **Persistent Memory** — Semantic search over agent interactions via vector embeddings
- **Sleep Consolidation** — Nightly background processes that boost important memories and prune irrelevant ones
- **Attention Reranking** — Psychological bias modeling (recency, frequency, importance) for intelligent retrieval
- **Local-First Architecture** — SQLite offline cache with optional cloud backend
- **Encryption & Privacy** — AES-256 encryption at rest, PII detection and redaction by default
- **Framework Agnostic** — Works with LangChain, OpenAI, HuggingFace, Ollama, Anthropic, and generic callables

### Key Features

| Feature | Details |
|---|---|
| **Memory Search** | Vector similarity + attention scoring |
| **Consolidation** | Background sleep phase pruning/boosting memories |
| **Encryption** | AES-256 on all stored memory content |
| **PII Protection** | Auto-detects and redacts emails, phone numbers, SSNs |
| **Offline Fallback** | SQLite cache works when API is unreachable |
| **Webhooks** | Events: `memory.stored`, `memory.archived`, `sleep.completed` |
| **Dashboard** | Memory Explorer, Search Preview, Analytics, Status Monitoring |
| **Batch Operations** | Write up to 100 memories in one call |
| **Export/Import** | Full memory state snapshots in JSON format |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Application                     │
│  (LangChain, OpenAI, HuggingFace, Ollama, or Custom)        │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐   ┌──────────┐   ┌─────────────┐
    │ Python  │   │ Offline  │   │ FastAPI     │
    │ SDK     │──▶│ SQLite   │──▶│ Backend     │
    │(wrap)   │   │ Cache    │   │ (Port 8000) │
    └─────────┘   └──────────┘   └──────┬──────┘
                                         │
          ┌──────────────┬───────────────┼───────────────┐
          ▼              ▼               ▼               ▼
     ┌─────────┐  ┌──────────┐  ┌─────────────┐  ┌──────────┐
     │PostgreSQL│  │ Embed    │  │ Celery      │  │ Redis    │
     │+pgvector │  │Service   │  │ Workers     │  │ Queue    │
     └─────────┘  └──────────┘  └─────────────┘  └──────────┘
                                         │
                                    ┌────▼─────┐
                                    │Dashboard  │
                                    │(React)    │
                                    │Port 3000  │
                                    └───────────┘
```

### Core Components

1. **Python SDK** (`sdk/python/neurosleepnet/`)
   - Agent wrapping and interception
   - Embedding generation
   - SQLite offline cache
   - Framework adapters

2. **FastAPI Backend** (`backend/app/`)
   - REST API for memory operations
   - PostgreSQL + pgvector integration
   - Authentication and rate limiting
   - Webhook management

3. **Embedding Service** (`services/embed/`)
   - Standalone FastEmbed service
   - Model caching
   - Low-latency embedding generation

4. **Celery Workers** (`backend/app/workers/`)
   - Sleep phase consolidation
   - Memory pruning and boosting
   - Webhook delivery
   - Audit logging

5. **React Dashboard** (`frontend/`)
   - Memory visualization
   - Search interface
   - Analytics and monitoring
   - Admin controls

---

## Prerequisites

- **Python 3.10+** (for backend and SDK)
- **Node.js 18+** (for frontend)
- **Docker & Docker Compose** (recommended for full stack)
- **PostgreSQL 14+** (if not using Docker)
- **Redis 6+** (if not using Docker)

Optional:
- **Make** (for convenient task running)
- **uv** (faster Python package manager alternative to pip)

---

## Installation

### Option 1: Docker Compose (Recommended)

Fastest way to get everything running:

```bash
git clone https://github.com/avirooppal/NeuroSleepNet.git
cd NeuroSleepNet

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec api python -m alembic upgrade head

# Seed demo data (optional)
docker-compose exec api python infra/scripts/seed_demo.py
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000
- **Embed Service**: http://localhost:8001

### Option 2: Local Development Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Setup environment variables
cp .env.example .env
# Edit .env with your settings

# Initialize database
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

#### Embed Service

```bash
cd services/embed

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start embedding service
python main.py
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Celery Workers

```bash
cd backend

source venv/bin/activate

# Start Celery worker
celery -A app.workers.tasks worker --loglevel=info

# Optional: Start beat scheduler for periodic tasks
celery -A app.workers.tasks beat --loglevel=info
```

#### Database

If running locally without Docker:

```bash
# PostgreSQL with pgvector
brew install postgresql   # or apt-get on Linux

# Create database
createdb neurosleepnet

# Enable pgvector
psql neurosleepnet -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
alembic upgrade head
```

---

## Project Structure

```
NeuroSleepNet/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── api/v1/                  # REST API endpoints
│   │   ├── core/                    # Core business logic
│   │   │   ├── attention.py         # Attention scoring
│   │   │   ├── consolidation.py     # Sleep phase logic
│   │   │   ├── embeddings.py        # Embedding handling
│   │   │   ├── sleep_engine.py      # Sleep consolidation engine
│   │   │   └── pii.py               # PII detection
│   │   ├── models/                  # Database models
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── services/                # Business logic services
│   │   ├── workers/                 # Celery tasks
│   │   ├── middleware/              # Auth, rate limit, audit
│   │   └── main.py                  # FastAPI app initialization
│   ├── alembic/                     # Database migrations
│   └── pyproject.toml               # Backend dependencies
│
├── sdk/
│   ├── python/                      # Python SDK package
│   │   ├── neurosleepnet/
│   │   │   ├── client.py            # API client
│   │   │   ├── cache.py             # SQLite offline cache
│   │   │   ├── wrappers.py          # Framework adapters
│   │   │   ├── embeddings.py        # Local embedding support
│   │   │   └── __init__.py          # Public API
│   │   └── examples/                # Usage examples
│   └── nodejs/                      # Node.js SDK (optional)
│
├── frontend/                         # React dashboard
│   ├── src/
│   │   ├── components/              # Reusable React components
│   │   ├── pages/                   # Page components
│   │   ├── store/                   # Zustand state management
│   │   ├── hooks/                   # Custom hooks
│   │   └── App.tsx                  # Main app component
│   ├── vite.config.ts               # Vite configuration
│   └── tailwind.config.ts           # Tailwind CSS config
│
├── services/
│   └── embed/                       # FastEmbed microservice
│       ├── main.py                  # Embedding service
│       └── requirements.txt         # Dependencies
│
├── infra/
│   ├── nginx/                       # Nginx reverse proxy config
│   └── scripts/                     # Setup/utility scripts
│
├── docs/                            # Documentation files
│   ├── integration-guides.md        # Framework integration examples
│   ├── api-reference.md             # API documentation
│   ├── error-reference.md           # Error codes
│   └── self-hosted.md               # Self-hosting guide
│
├── docker-compose.yml               # Local development stack
├── docker-compose.prod.yml          # Production stack
├── Dockerfile                       # Root Dockerfile
├── Makefile                         # Development commands
└── pyproject.toml                   # Root workspace configuration
```

### Key Directories

| Directory | Purpose |
|---|---|
| `backend/app/api/v1/` | API endpoints (routes) |
| `backend/app/core/` | Core algorithms (attention, consolidation, encryption) |
| `backend/app/models/` | SQLAlchemy database models |
| `backend/app/services/` | Business logic services |
| `backend/app/workers/` | Celery async task definitions |
| `sdk/python/neurosleepnet/` | Main SDK package for distribution |
| `frontend/src/components/` | React component library |
| `services/embed/` | Standalone embedding service |

---

## Development Setup

### Using Makefile

The project includes a Makefile with common development commands:

```bash
# Install development dependencies
make install

# Start all services with Docker Compose
make up

# Stop services
make down

# View logs
make logs

# Run tests
make test

# Run code quality checks
make lint

# Format code
make format

# Database migrations
make migrate

# Database rollback
make rollback
```

View all available commands:
```bash
make help
```

### Environment Variables

Create `.env` files in the respective directories:

**Backend** (`backend/.env`):
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/neurosleepnet
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key-change-this
EMBEDDING_API_URL=http://localhost:8001
ENVIRONMENT=development
```

**Frontend** (`frontend/.env.local`):
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=NeuroSleepNet Dev
```

**Embed Service** (`services/embed/.env`):
```env
MODEL_NAME=BAAI/bge-small-en-v1.5
PORT=8001
```

### Pre-commit Hooks

Setup pre-commit to run checks before commits:

```bash
pip install pre-commit
pre-commit install
```

---

## Running the Application

### Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild images
docker-compose up -d --build
```

### Local Development (All Services)

**Terminal 1 — Backend API:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Embed Service:**
```bash
cd services/embed
source venv/bin/activate
python main.py
```

**Terminal 3 — Celery Worker:**
```bash
cd backend
source venv/bin/activate
celery -A app.workers.tasks worker --loglevel=info
```

**Terminal 4 — Celery Beat (Scheduler):**
```bash
cd backend
source venv/bin/activate
celery -A app.workers.tasks beat --loglevel=info
```

**Terminal 5 — Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 6 — Database (if local PostgreSQL):**
```bash
postgres -D /usr/local/var/postgres  # Mac
# or on Linux: sudo service postgresql start
```

### Access Points

- **Frontend Dashboard**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc
- **Embed Service**: http://localhost:8001/health
- **PostgreSQL**: localhost:5432 (default credentials in docker-compose.yml)
- **Redis**: localhost:6379

---

## SDK Usage

### Basic Wrapping

```python
import neurosleepnet as nsn

# Initialize (connects to backend or uses offline cache)
nsn.init(
    api_key="your-api-key",
    base_url="http://localhost:8000"  # or cloud URL
)

# Wrap any agent/model
agent = nsn.wrap(your_agent)

# Use normally - memory is handled transparently
response = agent("Tell me about our previous session")
```

### Framework-Specific Examples

**LangChain AgentExecutor:**
```python
from langchain.agents import AgentExecutor
import neurosleepnet as nsn

agent = AgentExecutor.from_agent_and_tools(...)
wrapped_agent = nsn.wrap(agent)
wrapped_agent.invoke({"input": "What did I ask before?"})
```

**OpenAI API:**
```python
from openai import OpenAI
import neurosleepnet as nsn

client = OpenAI(api_key="...")
wrapped_client = nsn.wrap(client)

response = wrapped_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Remember this..."}]
)
```

**HuggingFace Pipeline:**
```python
from transformers import pipeline
import neurosleepnet as nsn

pipe = pipeline("text-generation", model="model-name")
wrapped_pipe = nsn.wrap(pipe)

result = wrapped_pipe("Query with memory context")
```

### Advanced API

```python
# Get memory status
status = nsn.status()
print(status.usage, status.latency, status.cache_hits)

# Manual memory operations
nsn.remember(
    content="Important fact",
    importance_score=0.9,
    context={"session_id": "abc123"}
)

# Search memory
results = nsn.search(
    query="previous project details",
    limit=5,
    min_score=0.7
)

# Batch operations
nsn.batch_remember([
    {"content": "fact1", "importance": 0.8},
    {"content": "fact2", "importance": 0.6},
])

# Export/Import memory
backup = nsn.export_memory()
nsn.import_memory(backup)
```

See [Integration Guide](docs/integration-guides.md) for more examples.

---

## API Documentation

### Core Endpoints

**POST /api/v1/auth/register**
Register a new account
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure-password",
    "full_name": "User Name"
  }'
```

**POST /api/v1/memories**
Store a new memory
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User preference: likes Python",
    "importance_score": 0.8,
    "context": {"type": "user_preference"}
  }'
```

**GET /api/v1/memories/search**
Search memories with attention scoring
```bash
curl -X GET "http://localhost:8000/api/v1/memories/search?query=user+preferences&limit=5" \
  -H "Authorization: Bearer <token>"
```

**POST /api/v1/batch/remember**
Batch store multiple memories
```bash
curl -X POST http://localhost:8000/api/v1/batch/remember \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "memories": [
      {"content": "fact1", "importance_score": 0.8},
      {"content": "fact2", "importance_score": 0.7}
    ]
  }'
```

See [API Reference](docs/api-reference.md) for complete endpoint documentation.

### Interactive API Explorer

Visit **http://localhost:8000/docs** to explore the API interactively with Swagger UI.

---

## Testing & Benchmarking

### Unit Tests

```bash
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Integration Tests

```bash
# Requires running services
pytest tests/integration/ -v -s
```

### Benchmarking SDK

```bash
cd sdk/python

# Run benchmark suite
pip install nsn-bench
nsn-bench run --model "your-model" --scenarios all

# Run specific scenarios
nsn-bench run --scenarios "multi_turn_recall,cross_session"

# Generate HTML report
nsn-bench report --output report.html
```

### Load Testing

```bash
# Using locust
pip install locust

cd backend
locust -f tests/load/locustfile.py \
  -u 100 \
  -r 10 \
  -t 5m \
  --headless
```

---

## Deployment

### Production Docker Stack

```bash
docker-compose -f docker-compose.prod.yml up -d

# Run migrations on production
docker-compose -f docker-compose.prod.yml \
  exec api alembic upgrade head
```

### Environment Setup for Production

```env
# backend/.env.prod
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:secure-pass@prod-db/neurosleepnet
REDIS_URL=redis://prod-redis:6379
JWT_SECRET=change-to-secure-random-value
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=info
```

### Monitoring & Observability

The backend includes:
- **Audit Logging** — All API actions logged to database
- **Rate Limiting** — Per-user and global rate limits
- **Health Checks** — `/health` and `/health/ready` endpoints
- **Metrics** — Prometheus-compatible metrics at `/metrics`

---

## Development Workflow

### Creating a New Feature

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Write tests first (TDD):**
   ```bash
   # backend/tests/test_my_feature.py
   ```

3. **Implement the feature:**
   - Backend logic in `backend/app/`
   - API endpoint in `backend/app/api/v1/`
   - Database model if needed in `backend/app/models/`

4. **Update schemas/migrations:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add my_feature"
   ```

5. **Test locally:**
   ```bash
   pytest tests/test_my_feature.py -v
   ```

6. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: add my-feature"
   git push origin feature/my-feature
   ```

7. **Create Pull Request** with description of changes

### Database Migrations

Adding a new column/table:

```bash
cd backend

# Auto-generate migration
alembic revision --autogenerate -m "description"

# Review generated migration in alembic/versions/
# Edit if needed

# Apply migration
alembic upgrade head
```

### Code Quality

**Format code:**
```bash
cd backend
black app/
isort app/
```

**Lint:**
```bash
cd backend
pylint app/
```

**Type checking:**
```bash
cd backend
mypy app/
```

---

## Troubleshooting

### Backend API Not Responding

```bash
# Check if service is running
curl http://localhost:8000/health

# View logs
docker-compose logs api

# Restart service
docker-compose restart api
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps

# Reset database (⚠️ deletes data)
docker-compose down -v
docker-compose up -d

# Recreate migrations
docker-compose exec api alembic upgrade head
```

### Embedding Service Timeout

```bash
# Check service health
curl http://localhost:8001/health

# Verify model is downloaded
docker-compose logs embed

# Restart service
docker-compose restart embed
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# Clear cache
docker-compose exec redis redis-cli FLUSHALL

# Restart
docker-compose restart redis
```

### Frontend Won't Load

```bash
# Clear node_modules and rebuild
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Celery Workers Not Processing Tasks

```bash
# Check worker is running
docker-compose logs worker

# Check Redis queue
docker-compose exec redis redis-cli

# Inside redis-cli:
> KEYS celery*
> LLEN celery

# Restart workers
docker-compose restart worker
```

---

## Contributing

### Code Style

- **Python**: PEP 8 (use Black for formatting)
- **TypeScript/React**: ESLint + Prettier configuration included
- **Git commits**: Conventional commits (`feat:`, `fix:`, `docs:`, etc.)

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run tests and linting locally
6. Commit with conventional commit messages
7. Push to your fork
8. Create Pull Request with clear description

### Reporting Issues

Use GitHub Issues with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

---

## Additional Resources

- **[Integration Guides](docs/integration-guides.md)** — Framework-specific examples
- **[API Reference](docs/api-reference.md)** — Complete endpoint documentation
- **[Error Reference](docs/error-reference.md)** — Error codes and solutions
- **[Self-Hosted Guide](docs/self-hosted.md)** — On-premise deployment
- **[GitHub Repository](https://github.com/avirooppal/NeuroSleepNet)**

---

## License

MIT License - See LICENSE file for details

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: palaviroopoff@gmail.com

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
