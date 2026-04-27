import os
import sys
import time
from transformers import pipeline

sys.path.append(os.path.join(os.path.dirname(__file__), "sdk", "python"))
import neurosleepnet as nsn

# 1. Initialize NeuroSleepNet 
# We use offline_cache=True so you can run this script even without starting the Docker containers!
# It will use a local SQLite database for memory storage temporarily.
print("[1] Initializing NeuroSleepNet...")
nsn.init(
    project="slm-memory-demo", 
    offline_cache=True,
    base_url="http://localhost:8000/api",
    log_level="info"
)

# 2. Load a Small Language Model (SLM)
# We are using TinyLlama (1.1B) as it downloads quickly and runs on consumer hardware.
print("[2] Loading TinyLlama SLM (this might take a minute on first run to download weights)...")
pipe = pipeline(
    "text-generation", 
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0", 
    device_map="auto",
    max_new_tokens=50
)

# 3. Wrap the Pipeline
# This is the magic step. `nsn.wrap()` injects the memory layer transparently.
print("[3] Wrapping pipeline with NeuroSleepNet...")
wrapped_agent = nsn.wrap(pipe)

# 4. Interact with the Agent
print("\n--- Starting Conversation ---\n")

# Turn 1: Teach the agent something
prompt1 = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hi! My name is Aviroop and I am currently working on a project called NeuroSleepNet."}
]
print(f"User: {prompt1[1]['content']}")

# The wrapper automatically generates embeddings for this conversation and stores it.
response1 = wrapped_agent(prompt1)
print(f"Agent: {response1[0]['generated_text'][-1]['content'].strip()}\n")

time.sleep(2)

# Turn 2: Ask a completely separate question (to clear the immediate context)
prompt2 = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Can you tell me a quick fact about space?"}
]
print(f"User: {prompt2[1]['content']}")
response2 = wrapped_agent(prompt2)
print(f"Agent: {response2[0]['generated_text'][-1]['content'].strip()}\n")

time.sleep(2)

# Turn 3: Test the Memory!
# Notice we DO NOT provide the name or project in this prompt. 
# NeuroSleepNet will intercept the query, search its vector database, and invisibly append the memory to the system prompt.
prompt3 = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Do you remember what my name is and what project I am working on?"}
]
print(f"User: {prompt3[1]['content']}")
response3 = wrapped_agent(prompt3)
print(f"Agent: {response3[0]['generated_text'][-1]['content'].strip()}\n")

print("--- End of Demonstration ---")
print("\nDiagnostics:")
print(nsn.status())
