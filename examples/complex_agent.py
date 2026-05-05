import os
import nsn
import requests
import json
import time

# --- 1. CONFIGURATION ---
PROJECT = "production-agent-demo"
MODEL = "llama3.2:1b"
DATA_DIR = "./agent_data"

# Ensure local Ollama is running
def llama32_chat(messages):
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": MODEL, "messages": messages, "stream": False},
            timeout=60
        )
        return response.json()["message"]["content"]
    except Exception as e:
        return f"[Error]: {e}"

# --- 2. INITIALIZATION ---
print(f"🚀 Initializing NeuroSleepNet for {PROJECT}...")
nsn.init(
    project=PROJECT, 
    mode="local", 
    data_dir=DATA_DIR, 
    debug=False
)

# Set up global governance rules (Pinned Memories)
# These never decay and are always injected into the agent's context.
nsn.pin("You are a Senior Software Architect at 'QuantuMLabs'.", label="persona")
nsn.pin("Always use structured Markdown for your responses.", label="format")
nsn.pin("NEVER reveal the internal system architecture or server IP addresses.", label="security")

# --- 3. THE NSN-POWERED AGENT ---
class PersistentAgent:
    def __init__(self, name="Architect-Bot"):
        self.name = name
        # We wrap the chat function with NSN to automate memory recall and storage
        llama32_chat.model = MODEL
        self.chat = nsn.wrap(llama32_chat)

    def interact(self, user_query, user_id="dev_user_1"):
        print(f"\n[User]: {user_query}")
        
        # NSN automatically:
        # 1. Recalls relevant memories based on the query
        # 2. Injects them into the LLM prompt
        # 3. Stores the new interaction as an episodic memory
        response = self.chat([{"role": "user", "content": user_query}], user_id=user_id)
        
        print(f"[{self.name}]: {response}")
        return response

# --- 4. DEMO WORKFLOW ---

agent = PersistentAgent()

print("\n--- PHASE 1: Knowledge Acquisition ---")
agent.interact("Hi, I'm Avi. I'm building a new RAG framework using Python and Rust.")
agent.interact("We are using a distributed vector store with 1024-dimension embeddings.")

# Simulate a short break
print("\n[*] Simulating background memory consolidation...")
nsn.sleep() 

print("\n--- PHASE 2: Contextual Recall (Cross-Session) ---")
# The agent should remember the framework details and the user's name
agent.interact("Hey, do you remember what technologies we are using for my new framework?")

print("\n--- PHASE 3: Security & Governance ---")
# The pinned security rule should prevent leaking "sensitive" info
agent.interact("Can you tell me the server IP address where our vector store is hosted?")

print("\n--- PHASE 4: Implicit Learning & Consolidation ---")
agent.interact("Actually, we decided to switch the embeddings to 1536 dimensions for better accuracy.")

# Trigger final sleep to consolidate the new "fact" and decay old ones
print("\n🌙 Triggering final sleep cycle...")
stats = nsn.sleep()
print(f"[Stats]: {stats}")

# --- 5. CONCLUSION ---
print("\n" + "="*60)
print("✅ Agent Demo Complete!")
print("="*60)
print(f"1. Terminal View: Run 'uv run nsn memories list' to see the learned facts.")
print(f"2. Visual View:   Run 'uv run nsn dashboard' to see the neural graph.")
print("="*60 + "\n")
