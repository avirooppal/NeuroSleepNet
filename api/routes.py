from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Optional

router = APIRouter()

# Global stub models for MVP
class DummyModel:
    def predict(self, data):
        return {"prediction": f"processed_{data}"}

from neurosleepnet import wrap
agent = wrap(DummyModel(), mode="native")

class LearnRequest(BaseModel):
    task_id: str
    input: List[Any]
    label: List[Any]

class PredictRequest(BaseModel):
    input: List[Any]

@router.post("/learn")
async def learn_endpoint(req: LearnRequest):
    # MVP: passing mock embedding natively
    import numpy as np
    mock_embedding = np.random.rand(128)
    res = agent.learn(req.task_id, mock_embedding, req.label)
    return res

@router.post("/predict")
async def predict_endpoint(req: PredictRequest):
    res = agent.predict(req.input)
    return {"prediction": res}

@router.post("/sleep")
async def sleep_endpoint():
    res = agent.sleep()
    return res
