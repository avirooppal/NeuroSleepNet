from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ..core.graph_store import GraphStore
from ..core.ingestion import IngestionEngine
from ..core.retriever import Retriever
from ..core.consolidation import ConsolidationEngine

router = APIRouter()

# Initialize core engines
store = GraphStore()
ingestion = IngestionEngine(store)
retriever = Retriever(store, ingestion)
consolidation = ConsolidationEngine(store)

class WriteRequest(BaseModel):
    user_id: str
    session_id: str
    messages: List[Dict[str, str]]
    task_id: Optional[str] = "default"

class ReadRequest(BaseModel):
    user_id: str
    query: str
    task_id: Optional[str] = "default"

@router.post("/v2/write")
def write_memory(req: WriteRequest, background_tasks: BackgroundTasks):
    ingestion.process_messages(
        user_id=req.user_id,
        session_id=req.session_id,
        task_id=req.task_id,
        messages=req.messages
    )
    # Trigger sleep replay asynchronously
    background_tasks.add_task(consolidation.run_consolidation, req.user_id)
    return {"status": "success"}

@router.post("/v2/read")
def read_memory(req: ReadRequest):
    context = retriever.retrieve(
        user_id=req.user_id,
        query=req.query,
        task_id=req.task_id
    )
    return {"context": context}
