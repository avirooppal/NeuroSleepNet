import neurosleepnet as nsn
import requests
import json
import time
import os

# 1. Initialize the NeuroSleepNet engine
# We use a specific project and local data directory
PROJECT = "llama-demo"
nsn.init(project=PROJECT, mode="local", data_dir="./demo_data", debug=True)

print(f"🚀 Starting NeuroSleepNet Demo with llama3.2:1b\n" + "="*50)

# 2. Setup Governance & Identity
print("📥 Setting up governance rules...")
nsn.pin("You are a specialized AI assistant powered by NeuroSleepNet persistent memory.", label="identity")
nsn.pin("Always maintain a professional and concise tone.", label="tone_guide")

# 3. Add Episodic & Semantic Memories for the Explorer
print("📥 Injecting user memories...")
USER_ID = "pioneer_01"
memories = [
    ("The user is an AI architect developing high-performance RAG systems.", "semantic", 0.9),
    ("The user recently presented at the Neuro-AI conference in Berlin.", "episodic", 0.8),
    ("The user's favorite coffee is a light-roast Ethiopian Yirgacheffe.", "episodic", 0.7),
    ("NeuroSleepNet solves context window limitations through consolidation.", "semantic", 1.0)
]

for content, m_type, importance in memories:
    nsn.remember(content, user_id=USER_ID, type=m_type, importance=importance)

# 4. Define real LLM wrapper for llama3.2:1b (via Ollama)
def llama32_llm(prompt: str) -> str:
    """Wrapper for local Ollama instance."""
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2:1b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        # Standard Ollama API call
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        return f"[Ollama Error]: Make sure ollama is running and llama3.2:1b is pulled. ({e})"

llama32_llm.model = "llama3.2:1b"

# 5. Wrap the LLM with NSN Memory
# This hooks into the prompt to inject retrieved context automatically
agent = nsn.wrap(llama32_llm, user_id=USER_ID)

# 6. Interactive Session to populate "Memory Pulse" (Hits/Misses)
print("\n🤖 Running Memory-Aware Interactions...")
interactions = [
    "What is my professional focus?",
    "Where did I recently present my work?",
    "How do I like my coffee?",
    "Tell me something about space exploration." # Expected to be a 'miss' to show in dashboard
]

for q in interactions:
    print(f"\n[User]: {q}")
    # NSN automatically retrieves context here
    response = agent(prompt=q)
    print(f"[Llama 3.2]: {response}")
    time.sleep(0.5)

# 7. Trigger Consolidation (Sleep)
# This will show activity in the "Memory Pulse" and "Sleep Log"
print("\n🌙 Triggering Sleep Cycle for memory consolidation...")
stats = nsn.sleep()
print(f"Consolidation complete: {stats}")

# 8. Finished!
print("\n" + "="*50)
print(f"✅ Demo execution complete.")
print(f"To view the persistent dashboard, run this in a new terminal:")
print(f"  PYTHONPATH=sdk/python uv run python -m neurosleepnet.cli dashboard --local --project {PROJECT} --data-dir ./demo_data")
print("="*50)

