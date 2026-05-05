import logging
from typing import List, Optional

import razorpay
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.user import User

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self) -> None:
        if settings.RAZORPAY_KEY_ID:
            self.client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        else:
            self.client = None

    def get_plans(self) -> List[dict]:
        """
        List available plans for the frontend.
        """
        return [
            {"id": settings.RAZORPAY_PLAN_ID_MONTHLY, "name": "Architect (Monthly)", "amount": 999, "interval": "monthly"},
            {"id": settings.RAZORPAY_PLAN_ID_ANNUAL, "name": "Architect (Annual)", "amount": 9999, "interval": "yearly"}
        ]

    async def create_subscription(
        self,
        session: AsyncSession,
        user: User,
        plan_id: str
    ) -> dict:
        """
        Create a Razorpay subscription for a user.
        """
        if not self.client:
            logger.warning("Razorpay key not set. Using mock subscription.")
            subscription_id = f"sub_mock_{user.id}"
        else:
            # Plan IDs come from Razorpay dashboard configuration
            subscription = self.client.subscription.create({
                "plan_id": plan_id,
                "total_count": 12,  # cycles
                "quantity": 1,
                "customer_notify": 1
            })
            subscription_id = subscription["id"]
            
        # Update user's temporary subscription ID (if needed)
        # Note: Plan is only updated on webhook success
        return {
            "subscription_id": subscription_id,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount": 999 if plan_id == settings.RAZORPAY_PLAN_ID_MONTHLY else 9999,
            "currency": "INR"
        }

    async def upgrade_user_to_paid(self, session: AsyncSession, razorpay_subscription_id: str) -> None:
        """
        Handle 'subscription.activated' or 'subscription.charged'.
        """
        query = select(User).where(User.razorpay_subscription_id == razorpay_subscription_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.plan = "paid"
            await session.commit()
            logger.info(f"User {user.id} upgraded to paid.")

    async def downgrade_user_to_free(self, session: AsyncSession, razorpay_subscription_id: str) -> None:
        """
        Handle 'subscription.cancelled' or 'subscription.expired'.
        """
        query = select(User).where(User.razorpay_subscription_id == razorpay_subscription_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.plan = "free"
            await session.commit()
            logger.info(f"User {user.id} downgraded to free.")


billing_service = BillingService()
