# NeuroSleepNet API Reference

This document provides comprehensive API documentation for NeuroSleepNet V2.

## Table of Contents

- [Core API](#core-api)
- [Memory Management](#memory-management)
- [Search and Retrieval](#search-and-retrieval)
- [Sleep and Synthesis](#sleep-and-synthesis)
- [Context Management](#context-management)
- [Error Handling](#error-handling)
- [Data Models](#data-models)

---

## Core API

### `nsn.init(**kwargs)`

Initialize NeuroSleepNet with configuration options.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `project` | str | "default" | Project name for isolation |
| `mode` | str | "local" | Storage mode: "local" or "self-host" |
| `host` | str | None | Remote host URL for self-host mode |
| `api_key` | str | None | API key for remote services |
| `memory_window` | int | 4096 | Context window size in tokens |
| `sleep_interval` | int | 300 | Sleep cycle interval in seconds |
| `sleep_on_exit` | bool | True | Trigger sleep on process exit |
| `embed_model` | str | "local" | Embedding provider |
| `recall_threshold` | float | None | Minimum similarity score for recall |
| `implicit_feedback` | bool | True | Enable implicit feedback collection |
| `decay` | bool | True | Enable memory decay over time |
| `model_family` | str | "generic" | Model family for context optimization |
| `debug` | bool | False | Enable debug logging |
| `data_dir` | str | "~/.neurosleepnet" | Data storage directory |
| `embedding_model` | str | None | Specific embedding model name |
| `synthesis_mode` | bool | False | Enable cognitive synthesis |

**Returns:** `None`

**Example:**
```python
import nsn

nsn.init(
    project="my-agent",
    mode="local",
    synthesis_mode=True,
    debug=True
)
```

---

### `nsn.wrap(func, **kwargs)`

Wrap an LLM function to add persistent memory capabilities.

**Parameters:**
| Parameter | Type | Description |
|-----------|-------|-------------|
| `func` | Callable | The LLM function to wrap |
| `top_k` | int | Number of memories to retrieve (default: adaptive) |
| `threshold` | float | Minimum similarity score (default: adaptive) |
| `implicit` | bool | Enable implicit feedback (default: True) |

**Returns:** `Callable` - Wrapped function with memory capabilities

**Example:**
```python
def my_llm(prompt: str) -> str:
    # Your LLM implementation
    return response

# Wrap with memory
agent = nsn.wrap(my_llm, top_k=5, threshold=0.7)

# Use normally
response = agent("What did we discuss about the project?")
```

---

## Memory Management

### `nsn.remember(content, **kwargs)`

Store a memory with optional metadata.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `content` | str | Required | Memory content text |
| `user_id` | str | None | User who owns this memory |
| `type` | str | "episodic" | Memory type |
| `importance` | float | 1.0 | Importance score (0.0-1.0) |
| `tags` | List[str] | [] | Associated tags |
| `ttl_days` | int | None | Time-to-live in days |
| `pinned` | bool | False | Whether to pin this memory |
| `label` | str | None | Human-readable label |
| `metadata` | Dict | {} | Additional metadata |

**Returns:** `NSNResult` - Result object with memory ID or error

**Example:**
```python
result = nsn.remember(
    "User prefers FastAPI over Flask",
    importance=0.8,
    tags=["preferences", "frameworks"],
    pinned=True
)

if result.ok:
    print(f"Stored memory with ID: {result.value['id']}")
else:
    print(f"Error: {result.error}")
```

### `nsn.forget(memory_id, **kwargs)`

Delete a specific memory.

**Parameters:**
| Parameter | Type | Description |
|-----------|-------|-------------|
| `memory_id` | str | ID of memory to delete |
| `user_id` | str | None | User ID for authorization |

**Returns:** `NSNResult`

### `nsn.forget_user(user_id)`

Delete all memories for a user.

**Parameters:**
| Parameter | Type | Description |
|-----------|-------|-------------|
| `user_id` | str | User ID whose memories to delete |

**Returns:** `NSNResult`

### `nsn.forget_project(project)`

Delete all memories for a project.

**Parameters:**
| Parameter | Type | Description |
|-----------|-------|-------------|
| `project` | str | Project name to clear |

**Returns:** `NSNResult`

---

## Search and Retrieval

### `nsn.recall(query, **kwargs)`

Retrieve memories based on semantic similarity.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `query` | str | Required | Search query text |
| `top_k` | int | 10 | Number of results to return |
| `user_id` | str | None | Filter by user |
| `type` | str | None | Filter by memory type |
| `min_importance` | float | None | Minimum importance threshold |
| `pinned_only` | bool | False | Only return pinned memories |

**Returns:** `NSNResult` - Result with list of memories or error

**Example:**
```python
result = nsn.recall(
    "What framework does the user prefer?",
    top_k=5,
    min_importance=0.5
)

if result.ok:
    for memory in result.value:
        print(f"Memory: {memory['content']}")
else:
    print(f"Recall failed: {result.error}")
```

### `nsn.search(query, **kwargs)`

Advanced search with filtering options.

**Parameters:** Same as `nsn.recall()` with additional:
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `date_range` | Tuple[str, str] | None | Date range filter (ISO8601) |
| `tags` | List[str] | None | Filter by tags |

**Returns:** `NSNResult`

### `nsn.list_memories(**kwargs)`

List memories with pagination and filtering.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `limit` | int | 100 | Maximum number to return |
| `offset` | int | 0 | Pagination offset |
| `user_id` | str | None | Filter by user |
| `type` | str | None | Filter by memory type |
| `sort_by` | str | "created_at" | Sort field |
| `sort_order` | str | "desc" | Sort order |

**Returns:** `NSNResult`

---

## Sleep and Synthesis

### `nsn.sleep()`

Manually trigger a sleep consolidation cycle.

**Returns:** `Dict` - Sleep cycle statistics

**Example:**
```python
stats = nsn.sleep()
print(f"Processed {stats['memories_processed']} memories")
print(f"Consolidated {stats['memories_consolidated']} memories")
```

### `nsn.sleep_status()`

Get current sleep cycle status.

**Returns:** `Dict` - Status information

### `nsn.sleep_pause()`

Pause automatic sleep cycles.

### `nsn.sleep_resume()`

Resume automatic sleep cycles.

---

## Context Management

### `NSNContext`

Explicit context class for managing multiple isolated NeuroSleepNet instances.

**Methods:**
- `init(**kwargs)` - Initialize context
- `shutdown()` - Clean up resources
- `remember(content, **kwargs)` - Store memory
- `recall(query, **kwargs)` - Retrieve memories
- `get_embedding(text)` - Get text embedding
- `apply_implicit_feedback(query)` - Apply feedback

**Example:**
```python
from neurosleepnet import NSNContext

# Create context for different projects
ctx1 = NSNContext()
ctx1.init(project="project1", mode="local")

ctx2 = NSNContext()
ctx2.init(project="project2", mode="local")

# Use independently
ctx1.remember("Project 1 data")
ctx2.remember("Project 2 data")
```

### `nsn.get_context(name)`

Get or create a named context.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `name` | str | "default" | Context name |

**Returns:** `NSNContext`

### `nsn.init_context(name, **kwargs)`

Initialize a named context.

**Parameters:**
| Parameter | Type | Description |
|-----------|-------|-------------|
| `name` | str | Context name |
| `**kwargs` | Any | Configuration options |

**Returns:** `NSNContext`

### `nsn.shutdown_context(name)`

Shutdown a named context.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `name` | str | "default" | Context name |

---

## Error Handling

### NSNResult

Result wrapper for API operations.

**Attributes:**
- `ok` (bool): Success status
- `value` (Any): Result value on success
- `error` (str): Error message on failure
- `error_code` (str): Machine-readable error code

**Methods:**
- `__bool__()`: Returns `ok` status

**Error Codes:**
- `EMBED_FAILED`: Embedding generation failed
- `STORE_FAILED`: Memory storage failed
- `RECALL_FAILED`: Memory retrieval failed
- `REMOTE_STORE_FAILED`: Remote storage failed
- `INVALID_PARAMS`: Invalid parameters

### Exception Classes

- `NSNInitError`: Initialization failed
- `NSNAuthError`: Authentication failed
- `NSNConnectionError`: Connection failed
- `NSNRecallError`: Recall operation failed

**Example:**
```python
from neurosleepnet import NSNResult, NSNRecallError

try:
    result = nsn.recall("query")
    if not result.ok:
        print(f"Error: {result.error} (Code: {result.error_code})")
except NSNRecallError as e:
    print(f"Recall failed: {e}")
```

---

## Data Models

### Memory

```python
{
    "id": "uuid",
    "content": "memory text",
    "user_id": "optional_user",
    "project": "project_name",
    "memory_type": "episodic|semantic|procedural|declarative",
    "status": "active|deprecated|archived",
    "importance": 0.0-1.0,
    "feedback_score": float,
    "consolidation_score": float,
    "access_count": int,
    "pinned": bool,
    "tags": ["tag1", "tag2"],
    "metadata": {...},
    "created_at": "ISO8601",
    "last_accessed_at": "ISO8601",
    "last_consolidated_at": "ISO8601",
    "ttl_days": int,
    "deprecated_by": "uuid",
    "label": "string"
}
```

### SearchResult

Memory with additional search relevance information:

```python
{
    # ... all Memory fields ...
    "attention_score": float,
    "why_retrieved": "reason for retrieval",
    "similarity": float
}
```

### SearchResponse

Complete search response:

```python
{
    "memories": [SearchResult],
    "total_found": int,
    "query_time_ms": float,
    "residual_context_applied": bool,
    "sleep_last_run": "ISO8601"
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|-----------|-------------|---------|
| `NSN_MODE` | Operation mode | "local" |
| `NSN_DATA_DIR` | Data directory | "~/.neurosleepnet" |
| `NSN_API_KEY` | API key for remote | None |
| `NSN_HOST` | Remote host URL | None |
| `NSN_DEBUG` | Enable debug | "false" |
| `NSN_EMBED_MODEL` | Embedding model | "local" |

### Configuration File

Create `.nsn.json` in your project root:

```json
{
    "project_id": "my-project",
    "data_dir": "./data",
    "mode": "local",
    "synthesis_mode": true,
    "debug": false
}
```

---

## Performance

### Benchmarks

| Operation | Latency (avg) | Throughput |
|------------|------------------|------------|
| Memory Store | 12ms | 1,000 ops/sec |
| Memory Recall | 8ms | 2,000 ops/sec |
| Vector Search | 15ms | 500 ops/sec |
| Sleep Cycle | 2.3s | 1 cycle/5min |

### Optimization Tips

1. **Use Local Mode**: Faster than remote for development
2. **Enable Caching**: Automatic for repeated content
3. **Batch Operations**: Use bulk operations when possible
4. **Optimize Queries**: Use specific filters to reduce search space
5. **Monitor Memory**: Use `nsn.stats()` to track performance

---

## Examples

### Basic Usage

```python
import nsn

# Initialize
nsn.init(project="my-agent")

# Store memories
nsn.remember("User is a Python developer")
nsn.remember("Working on FastAPI project", importance=0.8)

# Recall memories
memories = nsn.recall("What is the user working on?")

# Wrap LLM
agent = nsn.wrap(my_llm_function)
response = agent("Help me with the FastAPI project")
```

### Advanced Usage

```python
from neurosleepnet import NSNContext

# Multiple contexts
ctx1 = NSNContext()
ctx1.init(project="user1", synthesis_mode=True)

ctx2 = NSNContext()
ctx2.init(project="user2", synthesis_mode=False)

# Independent operations
ctx1.remember("User 1 data")
ctx2.remember("User 2 data")

# Error handling
result = ctx1.recall("query")
if not result.ok:
    if result.error_code == "RECALL_FAILED":
        # Handle recall failure
        pass
```

---

*For more detailed examples, see the [examples](../examples/) directory.*
