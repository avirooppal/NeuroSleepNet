import os
import time
import httpx
import subprocess
import json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))
import nsn

def run_command(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.stdout

def wait_for_api(url, timeout=300):
    start = time.time()
    print(f"Waiting for API at {url}...")
    while time.time() - start < timeout:
        try:
            res = httpx.get(url)
            if res.status_code == 200:
                print("API is UP!")
                return True
        except Exception:
            pass
        time.sleep(5)
    print("Timeout waiting for API.")
    return False

def main():
    # 1. Wait for health check
    if not wait_for_api("http://localhost:8080/health"):
        return

    # 2. Generate API Key
    print("Generating API Key...")
    output = run_command("docker compose exec api uv run python scripts/keygen.py")
    
    # Extract key from output (simple parsing)
    api_key = None
    for line in output.split("\n"):
        if "Key:" in line:
            api_key = line.split("Key:")[1].strip()
            break
    
    if not api_key:
        print("Failed to generate API key.")
        print(output)
        return
    
    print(f"Generated Key: {api_key}")

    # 3. Test SDK Connection
    print("Testing SDK Connection...")
    nsn.init(
        project="live-test",
        mode="self-host",
        host="http://localhost:8080/api",
        api_key=api_key
    )
    
    # Test remember
    print("Testing nsn.remember()...")
    mem = nsn.remember("The secret code is 42", user_id="user_live_1")
    print(f"Remember result: {mem}")
    
    # Wait for embedding worker to process
    print("Waiting for embedding...")
    time.sleep(5)
    
    # Test recall
    print("Testing nsn.recall()...")
    results = nsn.recall("What is the secret code?", user_id="user_live_1")
    print(f"Recall results: {results}")
    
    if results and "42" in results[0].get("content", ""):
        print("✅ LIVE VERIFICATION SUCCESSFUL!")
    else:
        print("❌ LIVE VERIFICATION FAILED: Result not as expected.")

if __name__ == "__main__":
    main()
