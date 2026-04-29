import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))
import nsn
import respx
import httpx
import pytest

@respx.mock
def test_self_host_init():
    # Mock ping
    respx.get("http://nsn-remote:8000/api/v1/ping").mock(
        return_value=httpx.Response(200, json={"status": "ok", "user_id": "test-user"})
    )
    
    print("Initializing NSN in self-host mode...")
    nsn.init(
        mode="self-host",
        host="http://nsn-remote:8000/api",
        api_key="nsn_sk_test_123",
        project="test-project"
    )
    
    config = nsn.get_config()
    assert config["mode"] == "self-host"
    assert config["host"] == "http://nsn-remote:8000/api"
    assert config["api_key"] == "nsn_sk_test_123"
    
    # Verify remember call
    # Note: NeuroSleepClient adds / to the path if not present, but _request prepends it.
    # url = f"{self.base_url}/{path.lstrip('/')}"
    # So /v1/memories/ becomes http://nsn-remote:8000/api/v1/memories/
    respx.post("http://nsn-remote:8000/api/v1/memories/").mock(
        return_value=httpx.Response(201, json={"id": "m1", "status": "active"})
    )
    
    print("Testing remember()...")
    nsn.remember("Hello world")
    
    # Verify recall call
    respx.get("http://nsn-remote:8000/api/v1/memories/retrieve").mock(
        return_value=httpx.Response(200, json={"memories": [{"memory": {"content": "Hello world"}, "attention_score": 0.9}]})
    )
    
    print("Testing recall()...")
    res = nsn.recall("Hello")
    assert any("Hello world" in m["memory"]["content"] for m in res)
    
    print("✅ SELF-HOST SDK VERIFICATION PASSED")

if __name__ == "__main__":
    test_self_host_init()
