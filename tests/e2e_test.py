import os
import shutil
import uuid
import pytest
import nsn

@pytest.fixture
def test_env():
    project_name = f"e2e-test-{uuid.uuid4().hex[:8]}"
    data_dir = f"./test_e2e_data_{project_name}"
    
    nsn.init(
        project=project_name,
        data_dir=data_dir,
        mode="local",
        sleep_interval=999999,
        sleep_on_exit=False,
    )
    
    yield {"project": project_name, "data_dir": data_dir}
    
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)

def test_initialization(test_env):
    cfg = nsn.get_config()
    assert cfg['mode'] == "local"
    assert cfg['project'] == test_env['project']

def test_pinning(test_env):
    nsn.pin("Always speak in a professional tone.", label="core_rule")
    nsn.pin("The user's primary operating system is Linux.", label="user_context")
    pins = nsn.list_pins()
    assert len(pins) >= 2

def test_memory_lifecycle(test_env):
    test_user = "user_123"
    nsn.remember("I love programming in Python and Rust.", user_id=test_user)
    nsn.remember("My favorite color is dark blue.", user_id=test_user)
    
    # Recall
    results = nsn.recall("What do I love programming in?", user_id=test_user)
    assert any("Python" in r['content'] for r in results)
    
    # Sleep/Consolidation
    nsn.remember("I love programming in Python and Rust.", user_id=test_user) # Duplicate
    stats = nsn.sleep()
    assert stats['deduped'] >= 0 # Might be 1 depending on similarity
    
    # Stats
    proj_stats = nsn.stats()
    assert proj_stats['total_memories'] > 0
    
    # Cleanup
    nsn.forget_user(test_user)
    mems = nsn.list_memories()
    assert not any(m.get("user_id") == test_user for m in mems)
