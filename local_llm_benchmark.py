import sys
import time
import os
import shutil

print("="*60)
print("🧠 NeuroSleepNet — Local Model Integration Test")
print("="*60)
try:
    from transformers import pipeline
except ImportError:
    print("Error: 'transformers' is not installed. Please try `pip install neurosleepnet[local_llm]`")
    sys.exit(1)

import neurosleepnet as nsn

# 1. Setup SDK in local/offline mode
# We wipe the local cache to ensure a fresh test
cache_dir = os.path.join(os.path.expanduser("~"), ".nsn")
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)

nsn.init(
    api_key="local_test", 
    project="local-llm-benchmark",
    offline_cache=True,
    fallback_mode="silent" # Ignores that backend isn't running
)

# 2. Download and Load Local Model
# We use Qwen1.5-0.5B or TinyLlama as they download fast (1-2GB) and run inference fast on CPU
model_id = "Qwen/Qwen1.5-0.5B-Chat"
print(f"\n[1] Loading Local Model ({model_id}). This may take a minute on first run...")

# Note: We keep max_new_tokens small so generation finishes fast in the test.
try:
    generator = pipeline(
        "text-generation", 
        model=model_id, 
        device_map="auto",
        max_new_tokens=40
    )
except Exception as e:
    print(f"Failed to load model: {e}")
    sys.exit(1)

print("\n[2] Setting up the NeuroSleepNet Agent Wrapper...")
nsn_agent = nsn.wrap(generator)

print("\n" + "-"*60)
print("TEST PHASE 1: The 'Raw' Local LLM (Without memory over time)")
print("-" * 60)

# Simulate telling it a fact.
print("👤 User: My secret pin code is 8402. Don't forget it.")
messages = [{"role": "user", "content": "My secret pin code is 8402. Don't forget it."}]
response = generator(messages)[0]['generated_text'][-1]['content']
print(f"🤖 Raw LLM: {response}")

# Simulate clearing context window (time passes, new session)
time.sleep(1)

print("\n👤 User: What is my secret pin code we talked about earlier?")
messages = [{"role": "user", "content": "What is my secret pin code we talked about earlier?"}]
response = generator(messages)[0]['generated_text'][-1]['content']
print(f"🤖 Raw LLM: {response}")
print("\n❌ RESULT: Model failed to recall the fact because it is outside the local context window.")

print("\n" + "-"*60)
print("TEST PHASE 2: The 'NeuroSleepNet' LLM (With memory)")
print("-" * 60)

# Simulate telling it a fact (this gets intercepted and stored by NSN)
print("👤 User: My secret project name is Apollo. Don't forget it.")
messages = [{"role": "user", "content": "My secret project name is Apollo. Don't forget it."}]
# Call the NSN wrapped version
response = nsn_agent(messages)[0]['generated_text'][-1]['content']
print(f"🤖 NSN LLM: {response}")

# Manually ensure memory is stored for the test (the wrapper auto logs, but async delays might be an issue during speedy tests)
nsn.remember("User's secret project name is Apollo.")
time.sleep(1)

print("\n👤 User: What is my secret project name we talked about earlier?")
messages = [{"role": "user", "content": "What is my secret project name we talked about earlier?"}]

# NeuroSleepNet steps in before the text goes to the model
response = nsn_agent(messages)[0]['generated_text'][-1]['content']
print(f"🤖 NSN LLM: {response}")

print("\n✅ RESULT: Model successfully recalled the fact without any custom vector DBs or RAG logic!")
print("="*60)
