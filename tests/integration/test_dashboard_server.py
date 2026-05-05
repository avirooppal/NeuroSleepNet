import time
import requests
import sqlite3
import os
import tempfile
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))
import nsn

data_dir = tempfile.mkdtemp()
nsn.init(project="dash-test", data_dir=data_dir, sleep_interval=999999, sleep_on_exit=False)

port = nsn.get_config()["dashboard_port"]
print(f"Server started on port {port}")

# Create some test data
nsn.remember("User is a frontend developer", type="semantic")
nsn.remember("Current task is building the dashboard", type="episodic")
nsn.pin("Always use React for frontend components")

time.sleep(0.5)

# Test endpoints
try:
    health = requests.get(f"http://localhost:{port}/api/health").json()
    print(f"Health: {health}")
    
    stats = requests.get(f"http://localhost:{port}/api/stats").json()
    print(f"Stats: memories={stats.get('total_memories')}, pins={stats.get('pinned')}")
    
    mems = requests.get(f"http://localhost:{port}/api/memories").json()
    print(f"Memories: {len(mems)}")
    
    pins = requests.get(f"http://localhost:{port}/api/pins").json()
    print(f"Pins: {len(pins)}")
    
    print("ALL API CALLS SUCCEEDED")
except Exception as e:
    print(f"API CALL FAILED: {e}")

import shutil
shutil.rmtree(data_dir)
