import os
import time
import subprocess
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))
import nsn

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

def main():
    print("--- Verifying Implicit Feedback (Checkpoint 5) ---")
    
    # 1. Setup
    output = run_command("docker compose exec api uv run python scripts/keygen.py")
    api_key = None
    for line in output.split("\n"):
        if "Key:" in line:
            api_key = line.split("Key:")[1].strip()
            break
    
    if not api_key:
        print("Failed to generate API key.")
        return

    nsn.init(
        project="feedback-test",
        mode="self-host",
        host="http://localhost:8080/api",
        api_key=api_key,
        debug=True
    )

    # 2. Inject a memory
    user_id = "tester_1"
    nsn.remember("The capital of France is Paris.", user_id=user_id)
    time.sleep(2) # Wait for embedding

    # 3. Define a dummy agent
    def my_agent(prompt):
        # This agent just echoes back something
        return "I recall that Paris is the capital of France."

    wrapped_agent = nsn.wrap(my_agent, user_id=user_id)

    # 4. First turn: Trigger recall
    print("\nTurn 1: Recalling memory...")
    wrapped_agent("Where is Paris?")
    
    # Verify memory was recalled
    mems = nsn.recall("Where is Paris?", user_id=user_id)
    if not mems:
        print("❌ Error: Memory not recalled.")
        return
    
    mem_id = mems[0]['id']
    initial_score = mems[0].get('feedback_score', 0.0)
    print(f"Memory ID: {mem_id[:8]}, Initial feedback_score: {initial_score}")

    # 5. Second turn: Send negative signal
    print("\nTurn 2: Sending negative implicit feedback ('No, that's wrong')...")
    wrapped_agent("No, that's wrong. Actually, it's Lyon.")

    # 6. Verify feedback was applied
    print("\nVerifying feedback application...")
    time.sleep(1) # Give it a moment to commit
    
    # We need to fetch the memory again to see the updated score
    # Note: nsn.recall() might return cached results if not careful, but the backend search_memories commits the update.
    updated_mems = nsn.recall("Where is Paris?", user_id=user_id)
    updated_score = updated_mems[0].get('feedback_score', 0.0)
    
    print(f"Updated feedback_score: {updated_score}")
    
    if updated_score < initial_score:
        print("✅ SUCCESS: Implicit feedback correctly downweighted the memory!")
    else:
        print("❌ FAILURE: feedback_score did not decrease.")

if __name__ == "__main__":
    main()
