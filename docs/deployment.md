# Deployment Guide

This guide covers various deployment scenarios for NeuroSleepNet V2.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Production Setup](#production-setup)
- [Monitoring](#monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- Memory: 4GB RAM
- Storage: 10GB available
- Python: 3.9+

**Recommended:**
- CPU: 4+ cores
- Memory: 8GB+ RAM
- Storage: 50GB+ SSD
- GPU: Optional for embeddings

### Dependencies

**Core:**
- Python 3.9+
- SQLite 3.35+ (local mode)
- Redis 6.0+ (self-host mode)
- PostgreSQL 13+ (self-host mode)

**Optional:**
- Docker 20.10+
- Kubernetes 1.20+
- Nginx 1.20+

---

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/NeuroSleepNet.git
cd NeuroSleepNet

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Configuration

Create `.env` file:
```bash
NSN_MODE=local
NSN_DATA_DIR=./data
NSN_DEBUG=true
NSN_PROJECT=my-dev-project
```

### Running Services

```bash
# Start dashboard
nsn dashboard --local --project my-project

# Run with hot reload
python -m neurosleepnet.server --reload
```

### Development Tools

```bash
# Code formatting
black neurosleepnet/
ruff check neurosleepnet/

# Run tests
pytest tests/ --cov=neurosleepnet

# Type checking
mypy neurosleepnet/
```

---

## Docker Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  neurosleepnet:
    build: .
    ports:
      - "8000:8000"
      - "3000:3000"  # Dashboard
    environment:
      - NSN_MODE=self-host
      - NSN_DB_URL=postgresql://nsn:password@postgres:5432/neurosleepnet
      - NSN_REDIS_URL=redis://redis:6379
      - NSN_API_KEY=${NSN_API_KEY}
      - NSN_EMBED_SERVICE_URL=http://embed-service:8001
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
      - embed-service

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=neurosleepnet
      - POSTGRES_USER=nsn
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  embed-service:
    build: ./services/embed
    ports:
      - "8001:8001"
    environment:
      - EMBED_MODEL=local
    volumes:
      - ./models:/app/models

volumes:
  postgres_data:
  redis_data:
```

### Running with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f neurosleepnet

# Stop services
docker-compose down
```

### Production Docker Image

```bash
# Build production image
docker build -t neurosleepnet:latest .

# Run with environment variables
docker run -d \
  --name neurosleepnet \
  -p 8000:8000 \
  -e NSN_MODE=self-host \
  -e NSN_DB_URL=postgresql://... \
  -e NSN_REDIS_URL=redis://... \
  -e NSN_API_KEY=your-api-key \
  neurosleepnet:latest
```

---

## Kubernetes Deployment

### Namespace and ConfigMaps

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: neurosleepnet
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nsn-config
  namespace: neurosleepnet
data:
  NSN_MODE: "self-host"
  NSN_DEBUG: "false"
  NSN_PROJECT: "production"
```

### Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nsn-secrets
  namespace: neurosleepnet
type: Opaque
data:
  db-url: <base64-encoded-db-url>
  redis-url: <base64-encoded-redis-url>
  api-key: <base64-encoded-api-key>
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neurosleepnet
  namespace: neurosleepnet
  labels:
    app: neurosleepnet
spec:
  replicas: 3
  selector:
    matchLabels:
      app: neurosleepnet
  template:
    metadata:
      labels:
        app: neurosleepnet
    spec:
      containers:
      - name: neurosleepnet
        image: neurosleepnet:latest
        ports:
        - containerPort: 8000
        - containerPort: 3000
        env:
        - name: NSN_MODE
          valueFrom:
            configMapKeyRef:
              name: nsn-config
              key: NSN_MODE
        - name: NSN_DB_URL
          valueFrom:
            secretKeyRef:
              name: nsn-secrets
              key: db-url
        - name: NSN_REDIS_URL
          valueFrom:
            secretKeyRef:
              name: nsn-secrets
              key: redis-url
        - name: NSN_API_KEY
          valueFrom:
            secretKeyRef:
              name: nsn-secrets
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/deep
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: neurosleepnet-service
  namespace: neurosleepnet
spec:
  selector:
    app: neurosleepnet
  ports:
  - name: api
    port: 8000
    targetPort: 8000
  - name: dashboard
    port: 3000
    targetPort: 3000
  type: LoadBalancer
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: neurosleepnet-ingress
  namespace: neurosleepnet
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.neurosleepnet.dev
    secretName: nsn-tls
  rules:
  - host: api.neurosleepnet.dev
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: neurosleepnet-service
            port:
              number: 8000
```

---

## Production Setup

### Environment Configuration

**Required Environment Variables:**
```bash
NSN_MODE=self-host
NSN_DB_URL=postgresql://user:password@host:5432/database
NSN_REDIS_URL=redis://host:6379
NSN_API_KEY=your-secure-api-key
```

**Optional Environment Variables:**
```bash
NSN_DATA_DIR=/app/data
NSN_LOG_LEVEL=INFO
NSN_MAX_CONNECTIONS=100
NSN_EMBED_SERVICE_URL=http://embed-service:8001
NSN_CORS_ORIGINS=https://yourdomain.com
```

### Database Setup

**PostgreSQL Configuration:**
```sql
-- Create database
CREATE DATABASE neurosleepnet;

-- Create user
CREATE USER nsn WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE neurosleepnet TO nsn;

-- Connect and run migrations
\c neurosleepnet
```

**Redis Configuration:**
```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### SSL/TLS Setup

**Nginx Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.neurosleepnet.dev;
    
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Monitoring

### Health Checks

**Basic Health:**
```bash
curl https://api.neurosleepnet.dev/health
```

**Deep Health:**
```bash
curl https://api.neurosleepnet.dev/health/deep
```

**Response:**
```json
{
  "status": "ok",
  "version": "2.0.0",
  "timestamp": "2024-05-09T12:00:00Z",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "embed": "ok"
  },
  "uptime_seconds": 86400
}
```

### Metrics

**Prometheus Metrics:**
- `/metrics` endpoint
- Memory usage
- Request latency
- Error rates
- Active connections

**Key Metrics:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Memory usage
process_resident_memory_bytes
```

### Logging

**Structured Logging:**
```json
{
  "timestamp": "2024-05-09T12:00:00Z",
  "level": "INFO",
  "service": "neurosleepnet",
  "trace_id": "abc123",
  "message": "Memory stored successfully",
  "user_id": "user123",
  "project": "my-project",
  "memory_id": "mem456"
}
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki
- Datadog

---

## Security

### Network Security

**Firewall Rules:**
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 8000/tcp  # Block direct API access
ufw deny 5432/tcp  # Block direct DB access
ufw deny 6379/tcp  # Block direct Redis access
```

**Rate Limiting:**
```nginx
# Nginx rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

server {
    location /api/v1/ {
        limit_req zone=api burst=20 nodelay;
    }
    
    location /api/v1/auth/ {
        limit_req zone=auth burst=10 nodelay;
    }
}
```

### Authentication

**API Key Management:**
```bash
# Generate secure API key
openssl rand -hex 32

# Hash with bcrypt
python -c "import bcrypt; print(bcrypt.hashpw(b'your-key', bcrypt.gensalt()))"
```

**JWT Configuration:**
```python
# JWT settings
JWT_SECRET_KEY = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
```

---

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check PostgreSQL status
systemctl status postgresql

# Test connection
psql -h localhost -U nsn -d neurosleepnet

# Check logs
tail -f /var/log/postgresql/postgresql.log
```

**2. Redis Connection Timeout**
```bash
# Check Redis status
redis-cli ping

# Monitor memory
redis-cli info memory

# Check logs
tail -f /var/log/redis/redis.log
```

**3. High Memory Usage**
```bash
# Check memory usage
free -h
top -p $(pgrep neurosleepnet)

# Monitor leaks
valgrind --leak-check=full python -m neurosleepnet
```

**4. Slow Queries**
```bash
# Enable slow query log
ALTER SYSTEM SET log_min_duration_statement = 1000;

# Analyze slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

### Performance Tuning

**Database Optimization:**
```sql
-- Create indexes
CREATE INDEX CONCURRENTLY idx_memories_project_status ON memories(project, status);
CREATE INDEX CONCURRENTLY idx_memories_created_at ON memories(created_at);

-- Update statistics
ANALYZE memories;

-- Configuration tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

**Redis Optimization:**
```conf
# redis.conf
tcp-keepalive 300
timeout 0
tcp-backlog 511
```

**Application Optimization:**
```python
# Connection pooling
DATABASE_POOL_SIZE = 20
REDIS_POOL_SIZE = 50

# Caching
CACHE_TTL = 3600
MAX_CACHE_SIZE = 10000
```

### Debug Mode

Enable debug logging:
```bash
export NSN_DEBUG=true
export NSN_LOG_LEVEL=DEBUG
```

Debug endpoints:
- `/debug/config` - Current configuration
- `/debug/stats` - Runtime statistics
- `/debug/health` - Detailed health info

---

## Scaling

### Horizontal Scaling

**Load Balancer Configuration:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: neurosleepnet-lb
spec:
  selector:
    app: neurosleepnet
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Session Affinity:**
```yaml
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 300
```

### Vertical Scaling

**Resource Requests:**
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

**Auto-scaling:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: neurosleepnet-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: neurosleepnet
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

*For additional support, see [troubleshooting.md](troubleshooting.md).*
