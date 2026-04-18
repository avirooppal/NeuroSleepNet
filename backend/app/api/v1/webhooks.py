from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def create_webhook(url: str):
    return {"url": url}
