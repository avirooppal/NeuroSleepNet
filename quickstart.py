"""
🧠 NeuroSleepNet - Quickstart & Tutorial

If you've been confused by how this works, this script explains everything step-by-step.
NeuroSleepNet is a "Memory Layer" for your AI. It intercepts what the AI sees, 
stores it efficiently, and retrieves it later so the AI doesn't forget past context.

Unlike Mem0, our focus is on:
1. High-accuracy retrieval (Integrating Hybrid search soon!)
2. Zero-ops setup (Runs entirely locally, no heavy databases required for testing)
3. Extremely low latency.
"""

from neurosleepnet import wrap

# ---------------------------------------------------------
# Step 1: Define Your Agent / LLM
# ---------------------------------------------------------
# Imagine this is a powerful LLM (like GPT-4 or Claude), 
# but here we use a dummy class to represent it.
class MyAgent:
    def predict(self, prompt: str):
        return f"[Agent Predicted Response to: '{prompt}']"

my_base_agent = MyAgent()

# ---------------------------------------------------------
# Step 2: Wrap the Agent with NeuroSleepNet
# ---------------------------------------------------------
# This is the magic. By wrapping the agent in "sidecar" mode, 
# NeuroSleepNet will automatically inject relevant memories 
# into the prompts BEFORE they reach your agent.
memory_agent = wrap(my_base_agent, mode="sidecar")

print("✅ Agent wrapped with NeuroSleepNet.")

# ---------------------------------------------------------
# Step 3: Teach the Agent (Store Memories)
# ---------------------------------------------------------
# The agent learns facts. We store these under a specific task or user session.
print("\n📚 Teaching the agent new facts...")

memory_agent.learn(
    task_id="user_session_123", 
    input_data="User Preference: TV model is Sony 77\" BRAVIA XR A80K",
    label="Fact"
)

memory_agent.learn(
    task_id="user_session_123", 
    input_data="User Preference: I prefer aisle seats when flying.",
    label="Fact"
)

# ---------------------------------------------------------
# Step 4: Retrieve & Predict (The Magic)
# ---------------------------------------------------------
# Now, we ask the agent a question. 
# Because it's wrapped, NeuroSleepNet automatically searches its memory 
# for relevant facts and secretly prepends them to the prompt!
print("\n🔍 Asking the agent a question (e.g. 'Which TV am I using?')...")
user_question = "Which TV am I using?"

# Notice we just call .predict(), exactly as we would normally!
response = memory_agent.predict(user_question, task_id="user_session_123")

print("\n--- Final Agent Output ---")
print(response)
print("--------------------------")

print("""
💡 Notice how the memory context was injected into the prompt? 
When you called `predict`, NeuroSleepNet executed a fast retrieval 
and appended the past context. Your base agent didn't have to be retrained!
Future iterations will introduce Hybrid Semantic+Keyword search for 95%+ accuracy.
""")
