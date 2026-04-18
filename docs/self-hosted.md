# Data Residency & Self-Hosted Deployment Guide

NeuroSleepNet can run entirely on your own infrastructure. No data leaves your network.

## Architecture Overview

```
Your Network
├── FastAPI Backend      (Postgres, Redis in same VPC)
├── Embedding Sidecar   (FastEmbed — no external API calls)
├── Sleep Engine Worker (Celery — isolated container)
└── SDK (Python)        (points to your backend URL)
```

All vector embeddings are generated locally via [FastEmbed](https://github.com/qdrant/fastembed). No OpenAI/Cohere API keys required.

---

## Quickstart (Docker Compose)

**Prerequisites:** Docker ≥ 24, docker compose ≥ 2.20

```bash
git clone https://github.com/your-org/neurosleepnet
cd neurosleepnet

# Copy and configure env
cp .env.example .env
# Edit .env — set NSN_ENCRYPTION_KEY, SECRET_KEY, POSTGRES_PASSWORD

docker compose -f docker-compose.prod.yml up -d
```

The stack will start on `http://localhost:8000`. Swagger docs at `/docs`.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `SECRET_KEY` | ✅ | JWT signing key (min 32 chars) |
| `NSN_ENCRYPTION_KEY` | ✅ | AES-256 key for memory content encryption (32 bytes) |
| `NSN_PII_DETECTION_ENABLED` | optional | Default `true`. Set `false` to disable PII scrubbing |
| `FASTEMBED_MODEL` | optional | Default `BAAI/bge-small-en-v1.5` |
| `CELERY_CONCURRENCY` | optional | Default `4` |

---

## Kubernetes Deployment

A Helm chart is provided in `infra/helm/neurosleepnet/`.

```bash
helm install nsn ./infra/helm/neurosleepnet \
  --set postgres.password="your-pg-pass" \
  --set redis.password="your-redis-pass" \
  --set encryptionKey="your-32-byte-key" \
  --set secretKey="your-jwt-secret"
```

### Resource Recommendations

| Service | CPU | Memory | Notes |
|---|---|---|---|
| Backend (FastAPI) | 0.5–2 cores | 512MB–2GB | Scale horizontally |
| Sleep Worker (Celery) | 1–2 cores | 1GB | 1 replica is sufficient |
| Embedding Sidecar | 2–4 cores | 2–4GB | CPU-bound; GPU optional |
| Postgres | 2+ cores | 4GB+ | Add pgvector extension |
| Redis | 0.5 cores | 256MB | Persistence optional |

---

## Data Isolation

Each user's memories are scoped by `user_id` at the database row level. All SQL queries include `WHERE user_id = :current_user_id`.  

For multi-tenant SaaS deployments, you can further isolate by:
- **Schema-per-tenant**: Create a Postgres schema per organization
- **Database-per-tenant**: Point `DATABASE_URL` to separate Postgres instances per tenant via connection pooling

---

## SDK Configuration

Point the SDK to your self-hosted backend:

```python
import neurosleepnet as nsn

nsn.init(
    api_key="your-self-hosted-api-key",  # Created via POST /v1/auth/register
    backend_url="https://your-nsn-instance.internal.company.com/v1",
    offline_cache=True  # Local SQLite fallback during outages
)
```

---

## Security Checklist

- [ ] Rotate `NSN_ENCRYPTION_KEY` — re-encrypt existing memories after rotation
- [ ] Enable TLS on all inter-service communication
- [ ] Restrict Postgres/Redis ports to internal network only
- [ ] Set `SECRET_KEY` to a cryptographically random 64-char string
- [ ] Enable Postgres row-level security if using schema-sharing multi-tenancy
- [ ] Back up the Postgres `memories` table — it is the source of truth

---

## Upgrading

```bash
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --no-deps backend sleep-worker
```

Database migrations run automatically on backend startup via SQLAlchemy `create_all`.

---

## Support

Self-hosted questions: open an issue tagged `self-hosted` on GitHub.
