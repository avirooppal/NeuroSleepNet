import os
import tempfile
import threading
import time
from datetime import datetime, timezone
import pytest
from neurosleepnet.embeddings import EmbeddingCache
from neurosleepnet.local_store import LocalStore
from neurosleepnet.local_sleep import _jaccard_synthesize, ContradictionSynthesizer
import neurosleepnet as nsn


def test_embedding_cache_invalidate():
    cache = EmbeddingCache()
    cache.add("mem-1", [0.1, 0.2, 0.3])
    cache.add("mem-2", [0.4, 0.5, 0.6])
    assert cache.size() == 2
    
    # Query forces flush
    res = cache.query([0.1, 0.2, 0.3], top_k=2)
    assert len(res) == 2
    assert cache._matrix is not None
    
    # Invalidate securely under lock
    cache.invalidate()
    assert cache._matrix is None
    assert len(cache._ids) == 0
    assert len(cache._pending) == 0
    assert cache.size() == 0


def test_local_store_synchronized_cache_lifecycle():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        store = LocalStore(data_dir=os.path.dirname(path))
        store.db_path = path # Override to dedicated temp DB
        store._init_db()
        
        # Manually warm
        cache = store._get_cache("test-project")
        assert cache is not None
        
        # Invalidate via run_consolidation simulation
        with store._cache_lock:
            store._caches["test-project"].invalidate()
            
        assert store._caches["test-project"]._matrix is None
        
        # Second call to _get_cache must trigger lazy re-warm gate
        cache_rewarmed = store._get_cache("test-project")
        assert cache_rewarmed is not None
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_temporal_contradiction_synthesis_scenarios():
    # Scenario 1: Direct factual contradiction
    cluster_1 = [
        {"id": "1", "content": "I use FastAPI.", "created_at": "2026-05-10 10:00:00"},
        {"id": "2", "content": "I switched to Django.", "created_at": "2026-05-12 12:00:00"},
    ]
    res_1 = _jaccard_synthesize(cluster_1)
    # Most recent sentence takes priority
    assert "I switched to Django." in res_1

    # Scenario 2: Complementary compound facts sharing framing vocabulary
    cluster_2 = [
        {"id": "1", "content": "I use FastAPI for the REST layer.", "created_at": "2026-05-10 10:00:00"},
        {"id": "2", "content": "I use Django for the admin panel.", "created_at": "2026-05-11 11:00:00"},
    ]
    res_2 = _jaccard_synthesize(cluster_2)
    # Both statements must be preserved since Jaccard token overlap <= 0.55
    assert "I use Django for the admin panel." in res_2
    assert "I use FastAPI for the REST layer." in res_2

    # Scenario 3: Sequential state updates pruning intermediate variations
    cluster_3 = [
        {"id": "1", "content": "My primary stack is Node.", "created_at": "2026-05-01 10:00:00"},
        {"id": "2", "content": "My primary stack is Python.", "created_at": "2026-05-05 10:00:00"},
        {"id": "3", "content": "My primary stack is Rust.", "created_at": "2026-05-10 10:00:00"},
    ]
    res_3 = _jaccard_synthesize(cluster_3)
    assert "My primary stack is Rust." in res_3
    assert "Node" not in res_3


def test_concurrent_cache_access_with_barrier():
    """
    Force multiple threads to simultaneously request _get_cache and add items
    while another thread calls invalidate(), proving thread-safety under barrier synchronization.
    """
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        store = LocalStore(data_dir=os.path.dirname(path))
        store.db_path = path
        store._init_db()

        num_threads = 5
        barrier = threading.Barrier(num_threads)
        errors = []

        def worker(thread_id):
            try:
                barrier.wait(timeout=5.0)
                if thread_id % 2 == 0:
                    cache = store._get_cache("concurrent-project")
                    with store._cache_lock:
                        cache.add(f"mem-{thread_id}", [0.1, 0.2, 0.3])
                else:
                    with store._cache_lock:
                        if "concurrent-project" in store._caches:
                            store._caches["concurrent-project"].invalidate()
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        final_cache = store._get_cache("concurrent-project")
        assert final_cache is not None
    finally:
        if os.path.exists(path):
            os.unlink(path)
