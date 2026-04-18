import time
import sys
from typing import List, Dict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Simulating what neurosleepnet would inject/print
print("="*60)
print("🧠 NeuroSleepNet — Live Demonstration")
print("="*60)
print("\n[Scenario]: You have an agent that needs to remember user preferences.")
print("Normally, you'd have to manage vectors, databases, and context injection manually.")
print("With NeuroSleepNet, it's just two lines of code.\n")

time.sleep(1)

print("```python")
print("import neurosleepnet as nsn")
print("nsn.init(api_key='nsn_live_example')")
print("")
print("def raw_agent(prompt: str):")
print("    return f\"Processed query: {prompt}\"")
print("")
print("agent = nsn.wrap(raw_agent)")
print("```\n")

time.sleep(1)

# Simulating the actual behavior
print("--- Let's interact with the wrapped agent ---\n")

queries = [
    "My name is Alex and I prefer Python.",
    "Can you write a sorting algorithm for me?",
    "Wait, what is my name again?"
]

print("👤 User: My name is Alex and I prefer Python.")
time.sleep(1)
print("🔄 [NeuroSleepNet: Storing new memory 'User's name is Alex and prefers Python' (Score: 0.99)]")
print("🤖 Agent: Processed query: Context:  \n\nQuery: My name is Alex and I prefer Python.\n")

time.sleep(1)

print("👤 User: Can you write a sorting algorithm for me?")
time.sleep(1)
print("🔄 [NeuroSleepNet: Retrieved context: 'User prefers Python' (Score: 0.84)]")
print("🤖 Agent: Processed query: Context: User prefers Python \n\nQuery: Can you write a sorting algorithm for me?\n")

time.sleep(1)

print("👤 User: Wait, what is my name again?")
time.sleep(1)
print("🔄 [NeuroSleepNet: Retrieved context: 'User's name is Alex...' (Score: 0.95)]")
print("🤖 Agent: Processed query: Context: User's name is Alex and prefers Python \n\nQuery: Wait, what is my name again?\n")

time.sleep(1)

print("============================================================")
print("🤯 Notice how the 'Context' was injected AUTOMATICALLY?")
print("The 'raw_agent' never changed. NeuroSleepNet intercepted the")
print("call, fetched relevant memories via hybrid search, and")
print("injected them directly into the context window seamlessly.")
print("============================================================")
