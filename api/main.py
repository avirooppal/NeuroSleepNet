from fastapi import FastAPI, WebSocket
from api.routes import router
import asyncio
import random
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NeuroSleepNet API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from neurosleepnet.server.api.routes import router as memory_v2_router
app.include_router(memory_v2_router, prefix="/api")

app.include_router(router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "NeuroSleepNet"}

@app.get("/api/tasks")
def get_tasks():
    # MVP stub for UI
    return {
        "tasks": [
            {"id": "t1", "accuracy": 0.91, "status": "active"},
            {"id": "t2", "accuracy": 0.88, "status": "active"},
            {"id": "t3", "accuracy": 0.79, "status": "warning"},
            {"id": "t4", "accuracy": 0.95, "status": "active"}
        ]
    }

@app.websocket("/ws/live")
async def live_risk_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # MVP: Emulate real-time risk stream
            risk = max(0.01, 0.05 + random.random() * 0.1 - 0.05)
            await websocket.send_json({"risk": risk})
            await asyncio.sleep(2)
    except Exception:
        pass
