# Troubleshooting Guide

This guide helps diagnose and resolve common issues with NeuroSleepNet V2.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Performance Issues](#performance-issues)
- [Memory Problems](#memory-problems)
- [Network Issues](#network-issues)
- [Database Issues](#database-issues)
- [Security Issues](#security-issues)
- [Debug Mode](#debug-mode)

---

## Installation Issues

### Python Version Incompatible

**Problem:** `ERROR: Python 3.9+ required`

**Solution:**
```bash
# Check Python version
python --version

# Install correct version
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3.9-pip

# macOS (with Homebrew)
brew install python@3.9

# Windows (with Chocolatey)
choco install python
```

### Dependency Conflicts

**Problem:** `ERROR: Could not resolve dependencies`

**Solution:**
```bash
# Create clean virtual environment
python -m venv nsn-env
source nsn-env/bin/activate  # Windows: nsn-env\Scripts\activate

# Install with specific version
pip install "neurosleepnet[local]==2.0.0"

# Clear pip cache if needed
pip cache purge
```

### Permission Denied

**Problem:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
# Use user directory
export NSN_DATA_DIR=~/.neurosleepnet

# Or fix permissions
sudo chown -R $USER:$USER ~/.neurosleepnet
chmod -R 755 ~/.neurosleepnet
```

---

## Configuration Problems

### Invalid Configuration

**Problem:** `NSNInitError: Invalid configuration`

**Solution:**
```python
import nsn

# Validate configuration
try:
    nsn.init(
        project="test",
        mode="local",
        debug=True
    )
except Exception as e:
    print(f"Config error: {e}")

# Check current config
print(nsn.get_config())
```

### Missing Environment Variables

**Problem:** `KeyError: NSN_DB_URL`

**Solution:**
```bash
# Set environment variables
export NSN_DB_URL="postgresql://user:pass@localhost:5432/nsn"
export NSN_REDIS_URL="redis://localhost:6379"

# Or use .env file
echo "NSN_DB_URL=postgresql://..." > .env
echo "NSN_REDIS_URL=redis://..." >> .env
```

### Port Already in Use

**Problem:** `OSError: [Errno 98] Address already in use`

**Solution:**
```bash
# Find process using port
lsof -i :8000
netstat -tulpn | grep :8000

# Kill process
kill -9 <PID>

# Or use different port
export NSN_PORT=8001
nsn.init(port=8001)
```

---

## Performance Issues

### Slow Memory Retrieval

**Problem:** Memory recall taking >1 second

**Diagnosis:**
```python
import time
import nsn

start = time.time()
result = nsn.recall("test query")
duration = time.time() - start

print(f"Recall took {duration:.3f}s")
```

**Solutions:**
1. **Enable Caching:**
   ```python
   nsn.init(cache_size=10000)
   ```

2. **Optimize Search:**
   ```python
   # Use specific filters
   nsn.recall("query", user_id="user123", top_k=5)
   ```

3. **Check Database Indexes:**
   ```sql
   -- Verify indexes exist
   \d+ memories
   ```

### High Memory Usage

**Problem:** Process using >2GB RAM

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep neurosleepnet
top -p $(pgrep neurosleepnet)

# Monitor over time
watch -n 1 'ps aux | grep neurosleepnet'
```

**Solutions:**
1. **Reduce Cache Size:**
   ```python
   nsn.init(cache_size=1000)  # Default is 10000
   ```

2. **Enable Memory Cleanup:**
   ```python
   nsn.init(decay=True, ttl_days=30)
   ```

3. **Use Background Sleep:**
   ```python
   nsn.init(sleep_interval=60)  # More frequent cleanup
   ```

### CPU Spiking

**Problem:** CPU usage consistently >80%

**Diagnosis:**
```bash
# Monitor CPU
top -p $(pgrep neurosleepnet)
htop -p $(pgrep neurosleepnet)

# Check thread count
ps -eLf | grep neurosleepnet
```

**Solutions:**
1. **Limit Concurrent Operations:**
   ```python
   nsn.init(max_workers=4)
   ```

2. **Disable Resource-Intensive Features:**
   ```python
   nsn.init(synthesis_mode=False)  # Disable background synthesis
   ```

---

## Memory Problems

### Memory Not Persisting

**Problem:** `nsn.remember()` succeeds but `nsn.recall()` returns empty

**Diagnosis:**
```python
import nsn

# Store memory
result = nsn.remember("test memory")
print(f"Store result: {result}")

# Check database directly
import sqlite3
conn = sqlite3.connect("~/.neurosleepnet/neurosleepnet.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM memories WHERE content LIKE '%test%'")
print(cursor.fetchall())
```

**Solutions:**
1. **Check Database Path:**
   ```python
   import os
   print(f"Data directory: {os.path.expanduser('~/.neurosleepnet')}")
   ```

2. **Verify Write Permissions:**
   ```bash
   ls -la ~/.neurosleepnet/
   touch ~/.neurosleepnet/test.db
   ```

3. **Check Transactions:**
   ```python
   # Ensure commit happens
   nsn.init(auto_commit=True)
   ```

### Duplicate Memories

**Problem:** Same content stored multiple times

**Diagnosis:**
```python
# Check for duplicates
import nsn
result = nsn.recall("specific phrase", exact_match=True)
print(f"Found {len(result.value)} duplicates")
```

**Solutions:**
1. **Enable Deduplication:**
   ```python
   nsn.init(deduplication=True, similarity_threshold=0.95)
   ```

2. **Use Unique Constraints:**
   ```sql
   -- Add unique constraint
   ALTER TABLE memories ADD CONSTRAINT unique_content UNIQUE (content_hash);
   ```

### Memory Corruption

**Problem:** `sqlite3.DatabaseError: database disk image is malformed`

**Solutions:**
1. **Backup and Recreate:**
   ```bash
   cp ~/.neurosleepnet/neurosleepnet.db ~/.neurosleepnet/backup.db
   rm ~/.neurosleepnet/neurosleepnet.db
   # Restart application to recreate
   ```

2. **Run Integrity Check:**
   ```bash
   sqlite3 ~/.neurosleepnet/neurosleepnet.db "PRAGMA integrity_check;"
   ```

---

## Network Issues

### Connection Refused

**Problem:** `ConnectionRefusedError: [Errno 61] Connection refused`

**Diagnosis:**
```bash
# Check if service is running
netstat -tulpn | grep :8000
curl http://localhost:8000/health
```

**Solutions:**
1. **Start Service:**
   ```bash
   python -m neurosleepnet.server
   ```

2. **Check Firewall:**
   ```bash
   # Ubuntu/Debian
   sudo ufw status
   sudo ufw allow 8000
   
   # CentOS/RHEL
   sudo firewall-cmd --list-all
   sudo firewall-cmd --add-port=8000/tcp --permanent
   ```

### Timeout Issues

**Problem:** `TimeoutError: Request timed out after 30 seconds`

**Solutions:**
1. **Increase Timeout:**
   ```python
   nsn.init(timeout=60)
   ```

2. **Check Network Latency:**
   ```bash
   ping -c 4 your-api-host
   traceroute your-api-host
   ```

3. **Use Connection Pooling:**
   ```python
   nsn.init(pool_size=20, max_connections=100)
   ```

### SSL/TLS Issues

**Problem:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions:**
1. **Verify Certificate:**
   ```bash
   openssl s_client -connect your-host:443 -showcerts
   ```

2. **Update CA Bundle:**
   ```bash
   # Update certifi
   pip install --upgrade certifi
   ```

3. **Disable Verification (Development Only):**
   ```python
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   ```

---

## Database Issues

### Connection Pool Exhausted

**Problem:** `Too many connections to database`

**Diagnosis:**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Check max connections
SHOW max_connections;
```

**Solutions:**
1. **Increase Pool Size:**
   ```python
   nsn.init(db_pool_size=50)
   ```

2. **Enable Connection Recycling:**
   ```python
   nsn.init(db_recycle_seconds=3600)
   ```

3. **Monitor Connections:**
   ```python
   # Enable connection logging
   nsn.init(log_connections=True)
   ```

### Database Locked

**Problem:** `sqlite3.OperationalError: database is locked`

**Solutions:**
1. **Enable WAL Mode:**
   ```python
   nsn.init(journal_mode="WAL")
   ```

2. **Increase Timeout:**
   ```python
   nsn.init(db_timeout=30.0)
   ```

3. **Check for Long-Running Transactions:**
   ```sql
   -- Find long transactions
   SELECT pid, age(clock_timestamp(), query_start) AS age, query 
   FROM pg_stat_activity 
   WHERE state != 'idle' AND age > '5 minutes';
   ```

### Migration Failures

**Problem:** `Migration failed: Already exists`

**Solutions:**
1. **Check Migration Status:**
   ```bash
   python -m alembic current
   python -m alembic history
   ```

2. **Reset Migrations:**
   ```bash
   python -m alembic downgrade base
   python -m alembic upgrade head
   ```

3. **Manual Migration:**
   ```sql
   -- Apply missing migration manually
   ALTER TABLE memories ADD COLUMN IF NOT EXISTS consolidation_score FLOAT;
   ```

---

## Security Issues

### API Key Authentication Failed

**Problem:** `401 Unauthorized: Invalid API key`

**Diagnosis:**
```bash
# Test API key
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/auth/verify
```

**Solutions:**
1. **Regenerate API Key:**
   ```python
   import nsn
   new_key = nsn.generate_api_key()
   print(f"New key: {new_key}")
   ```

2. **Check Key Format:**
   ```bash
   # Ensure no whitespace
   echo "$NSN_API_KEY" | xargs
   ```

### CORS Errors

**Problem:** `No 'Access-Control-Allow-Origin' header`

**Solutions:**
1. **Configure Allowed Origins:**
   ```python
   nsn.init(cors_origins=["https://yourdomain.com"])
   ```

2. **Development Mode:**
   ```python
   nsn.init(cors_allow_all=True)  # Development only!
   ```

### Rate Limiting

**Problem:** `429 Too Many Requests`

**Diagnosis:**
```bash
# Check rate limit headers
curl -I http://localhost:8000/api/v1/memories
```

**Solutions:**
1. **Increase Limits:**
   ```python
   nsn.init(rate_limit=1000)  # requests per hour
   ```

2. **Use API Key with Higher Limits:**
   ```python
   nsn.init(api_key="premium-key")
   ```

---

## Debug Mode

### Enabling Debug Mode

**Basic Debug:**
```python
import nsn

nsn.init(debug=True)
```

**Environment Variable:**
```bash
export NSN_DEBUG=true
export NSN_LOG_LEVEL=DEBUG
```

**Debug Configuration:**
```python
nsn.init(
    debug=True,
    log_level="DEBUG",
    log_file="nsn-debug.log",
    profile_performance=True
)
```

### Debug Information

**Current Configuration:**
```python
import nsn

print("Current config:")
print(nsn.get_config())
```

**Memory Statistics:**
```python
stats = nsn.stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Cache hit rate: {stats['cache_hit_rate']}%")
print(f"Average recall time: {stats['avg_recall_time']}ms")
```

**Health Check:**
```python
health = nsn.health_check()
print(f"Database: {health['database']}")
print(f"Redis: {health['redis']}")
print(f"Embedding service: {health['embedding']}")
```

### Performance Profiling

**Enable Profiling:**
```python
import cProfile
import pstats

# Profile memory operations
profiler = cProfile.Profile()
profiler.enable()

# Run operations
nsn.remember("test")
nsn.recall("test")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

**Memory Profiling:**
```python
import tracemalloc

# Start tracing
tracemalloc.start()

# Run operations
nsn.remember("test" * 1000)

# Get snapshot
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

---

## Getting Help

### Collect Debug Information

**System Information:**
```bash
# Create debug report
python -c "
import platform
import sys
import nsn

print('=== NeuroSleepNet Debug Report ===')
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'NSN Version: {nsn.__version__}')
print(f'Config: {nsn.get_config()}')
print('=====================================')
"
```

**Log Collection:**
```bash
# Collect recent logs
tail -n 100 ~/.neurosleepnet/logs/nsn.log > debug-logs.txt

# Include system logs
journalctl -u neurosleepnet --since "1 hour ago" >> debug-logs.txt
```

### Support Channels

- **GitHub Issues**: https://github.com/your-org/NeuroSleepNet/issues
- **Discord**: https://discord.gg/neurosleepnet
- **Email**: support@neurosleepnet.dev
- **Documentation**: https://docs.neurosleepnet.dev

When reporting issues, please include:
1. NeuroSleepNet version
2. Python version
3. Operating system
4. Error message and traceback
5. Steps to reproduce
6. Debug information (if applicable)

---

*Last updated: May 9, 2024*
