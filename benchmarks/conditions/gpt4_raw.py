import os
import httpx

# Note: Requires OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def run(prompt: str, user_id: str = "benchmark_user"):
    # No memory, fresh context each time
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY not set"
        
    try:
        response = httpx.post("https://api.openai.com/v1/chat/completions", headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }, json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }, timeout=60.0)
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"
