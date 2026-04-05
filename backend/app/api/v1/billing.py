import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


from ...deps import get_db
from ...models.user import User
from ...schemas import billing as billing_schema
from ...services.billing_service import billing_service
from .auth import get_current_user
from ...config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/plans", response_model=billing_schema.PlanList)
async def get_plans_list():
    """
    Get available subscription plans.
    """
    return {"plans": billing_service.get_plans()}


@router.post("/subscribe", response_model=billing_schema.SubscriptionResponse)
async def create_subscription(
    sub_in: billing_schema.SubscriptionInit,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a Razorpay subscription.
    """
    return await billing_service.create_subscription(
        session=db,
        user=current_user,
        plan_id=sub_in.plan_id
    )


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Annotated[str, Header()],
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Razorpay webhooks (subscription.activated, etc).
    """
    body = await request.body()
    
    # 1. Verify signature
    # In a real app, use razorpay client to verify signature
    # (Mocking safety check for now)
    try:
        # billing_service.client.utility.verify_webhook_signature(body, x_razorpay_signature, settings.RAZORPAY_WEBHOOK_SECRET)
        data = json.loads(body)
        event = data.get("event")
        payload = data.get("payload", {})
        
        # 2. Extract subscription ID
        sub_id = payload.get("subscription", {}).get("entity", {}).get("id")
        
        if event == "subscription.activated":
            await billing_service.upgrade_user_to_paid(db, sub_id)
        elif event == "subscription.cancelled":
            await billing_service.downgrade_user_to_free(db, sub_id)
            
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
