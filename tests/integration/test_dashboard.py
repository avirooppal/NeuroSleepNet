import time
import requests
import os
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))

import nsn

# Clean start
DATA_DIR = "./test_dashboard_data"
if os.path.exists(DATA_DIR):
    shutil.rmtree(DATA_DIR)

def test_dashboard_api():
    print("Initializing NSN project: dashboard-test")
    nsn.init(project="dashboard-test", data_dir=DATA_DIR, debug=True)
    
    # Get port
    from neurosleepnet import _config
    port = _config["dashboard_port"]
    base_url = f"http://localhost:{port}"
    print(f"Dashboard server running on {base_url}")

    # Add some data
    print("Storing memories...")
    nsn.remember("I love Python", user_id="u1")
    nsn.remember("I hate Javascript", user_id="u1")
    
    print("Pinning a rule...")
    nsn.pin("Always be polite", label="politeness")
    
    print("Creating a miss...")
    # Recall with low threshold so it hits, then high so it misses
    nsn.recall("What do I like?", user_id="u1") # This should hit and be in memories
    
    # Force a miss by setting a very high threshold via override if possible, 
    # or just use the default which might miss if score is low.
    # Actually, let's just recall something completely unrelated.
    nsn.recall("What is the weather in Mars?", user_id="u1")
    
    # Wait a bit for events to push
    time.sleep(1)

    # Check API Endpoints
    print("\nVerifying API endpoints:")
    
    # Stats
    resp = requests.get(f"{base_url}/api/stats?project=dashboard-test")
    print(f"GET /api/stats: {resp.status_code}")
    stats = resp.json()
    print(f"Stats: memories={stats['total_memories']}, pins={stats['pinned']}, miss_count={stats['miss_count']}")
    assert stats['total_memories'] >= 2
    assert stats['pinned'] == 1
    
    # Memories
    resp = requests.get(f"{base_url}/api/memories?project=dashboard-test")
    print(f"GET /api/memories: {resp.status_code}")
    mems = resp.json()
    print(f"Memories count: {len(mems)}")
    assert len(mems) >= 2
    
    # Pins
    resp = requests.get(f"{base_url}/api/pins?project=dashboard-test")
    print(f"GET /api/pins: {resp.status_code}")
    pins = resp.json()
    print(f"Pins count: {len(pins)}")
    assert len(pins) == 1
    assert pins[0]['label'] == 'politeness'
    
    # Misses
    resp = requests.get(f"{base_url}/api/misses?project=dashboard-test")
    print(f"GET /api/misses: {resp.status_code}")
    misses = resp.json()
    print(f"Misses count: {len(misses)}")
    # Depending on embeddings, it might or might not miss. 
    # But we called recall twice, one should have low score.
    
    # Static Assets
    resp = requests.get(f"{base_url}/index.html")
    print(f"GET /index.html: {resp.status_code}")
    assert resp.status_code == 200
    assert "<title>" in resp.text
    
    # Trigger Sleep
    print("Triggering sleep via API...")
    resp = requests.post(f"{base_url}/api/sleep")
    print(f"POST /api/sleep: {resp.status_code}")
    assert resp.status_code == 200
    assert resp.json()['status'] == 'triggered'
    
    # Wait for sleep to finish
    time.sleep(2)
    resp = requests.get(f"{base_url}/api/stats?project=dashboard-test")
    stats = resp.json()
    print(f"Stats after sleep: cycles={stats['sleep_cycles_run']}")
    assert stats['sleep_cycles_run'] >= 1

    print("\n✅ DASHBOARD VERIFICATION PASSED")

if __name__ == "__main__":
    try:
        test_dashboard_api()
    finally:
        # Give a moment for background threads to exit if needed, 
        # but NSN uses daemon threads for dashboard.
        pass
