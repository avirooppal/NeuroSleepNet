import nsn
import requests

# 1. Define your simple LLM function (Ollama/Llama 3.2 1b)
def llama_chat(messages):
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    resp = requests.post("http://localhost:11434/api/chat", 
                         json={"model": "llama3.2:1b", "messages": messages, "stream": False})
    if resp.status_code != 200:
        return f"[Error from Ollama]: {resp.text}"
    return resp.json().get("message", {}).get("content", "No content")

# 2. THE THREE LINES OF MAGIC
llama_chat.model = "llama3.2:1b"
chat = nsn.wrap(llama_chat)  # Auto-initializes with smart defaults if init() is skipped

# --- Test the magic ---
print("Turn 1: Teaching the agent...")
print("Agent:", chat("My name is Avi and I love building robots."))

print("\nTurn 2: Cross-session recall (automatic)...")
# The agent will automatically recall the name 'Avi' and 'robots' because of nsn.wrap
print("Agent:", chat("Do you remember my name?"))

print("\n✨ Magic is happening! Memory is now persistent and automatic.")
print("Check the dashboard: uv run nsn dashboard")
