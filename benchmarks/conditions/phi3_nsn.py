import os
import sys
import httpx
import nsn

# Add SDK to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "sdk", "python")))

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"

def llama_model(prompt: str, **kwargs) -> str:
    try:
        response = httpx.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 256}
        }, timeout=60.0)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error: {e}"

# Set model name attribute
llama_model.model = MODEL_NAME

# Global initialization
nsn.init(
    project="benchmark-nsn", 
    mode="local", 
    model_family="llama3", # Force llama3 to use my new template
    recall_threshold=0.2,  # Fairly lenient but not noisy
    data_dir="./benchmark_data/nsn"
)
wrapped_model = nsn.wrap(llama_model)

def run(prompt: str, user_id: str = "benchmark_user"):
    return wrapped_model(prompt, user_id=user_id)
