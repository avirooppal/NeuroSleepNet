import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastembed import TextEmbedding

app = FastAPI(title="NeuroSleepNet Embed Sidecar")

# Load model globally on startup
model_name = os.getenv("MODEL", "BAAI/bge-small-en-v1.5")
embedding_model = TextEmbedding(model_name=model_name)

class EmbedRequest(BaseModel):
    texts: List[str]

@app.get("/health")
def health_check():
    return {"status": "ok", "model": model_name}

@app.post("/v1/embed")
def generate_embeddings(request: EmbedRequest):
    # embedding_model.embed returns a generator of numpy arrays
    embeddings = list(embedding_model.embed(request.texts))
    # Convert numpy arrays to nested lists
    encoded = [emb.tolist() for emb in embeddings]
    return {"embeddings": encoded}
