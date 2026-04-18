import pytest
import os
import tempfile
import sqlite3
from neurosleepnet.cache import OfflineCache

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    os.unlink(path)

def test_cache_init(temp_db):
    cache = OfflineCache(db_path=temp_db)
    import contextlib
    # Check if table is created
    with contextlib.closing(sqlite3.connect(temp_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories_cache'")
        assert cursor.fetchone() is not None

def test_cache_store_and_retrieve(temp_db):
    cache = OfflineCache(db_path=temp_db)
    
    # Store
    cache.store("User likes JSON", project="test_proj", session_id="123", tags=["prefs"], importance=0.9)
    cache.store("User likes YAML", project="test_proj", session_id="123", tags=["prefs"], importance=0.5)
    cache.store("Different project", project="other_proj", session_id="456")
    
    # Retrieve
    memories = cache.retrieve(project="test_proj", limit=5)
    assert len(memories) == 2
    assert "User likes YAML" in memories[0]["content"]  # latest first due to ORDER BY timestamp DESC
    assert "User likes JSON" in memories[1]["content"]
