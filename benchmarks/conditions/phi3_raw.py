import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"

def run(prompt: str, user_id: str = "benchmark_user"):
    try:
        response = httpx.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 128}
        }, timeout=60.0)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error: {e}"
