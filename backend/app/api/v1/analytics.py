from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def memory_health():
    return {"status": "excellent"}

@router.get("/usage")
def memory_usage():
    return {"calls": 0, "tokens": 0}

@router.get("/timeline")
def memory_timeline():
    return []
