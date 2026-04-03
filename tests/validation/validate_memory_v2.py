
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_v2_memory_write_and_read():
    # 1. Write memories
    write_resp = client.post("/api/v2/write", json={
        "user_id": "test_user_1",
        "session_id": "sess_1",
        "task_id": "coding_task",
        "messages": [
            {"role": "user", "content": "I like writing Python in VS Code."},
            {"role": "user", "content": "My favorite framework is FastAPI."}
        ]
    })
    
    assert write_resp.status_code == 200, write_resp.text
    assert write_resp.json()["status"] == "success"

    # 2. Read memories
    read_resp = client.post("/api/v2/read", json={
        "user_id": "test_user_1",
        "query": "What framework do I like?",
        "task_id": "coding_task"
    })
    
    assert read_resp.status_code == 200, read_resp.text
    ctxt = read_resp.json()["context"]
    assert "FastAPI" in ctxt or "VS Code" in ctxt
    print("✅ E2E Integration Test Passed. Context retrieved:", ctxt)
    
if __name__ == "__main__":
    test_v2_memory_write_and_read()
