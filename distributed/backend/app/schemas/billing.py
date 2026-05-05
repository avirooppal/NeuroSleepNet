from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PlanInfo(BaseModel):
    id: str
    name: str
    amount: int
    interval: str


class PlanList(BaseModel):
    plans: List[PlanInfo]


class SubscriptionInit(BaseModel):
    plan_id: str


class SubscriptionResponse(BaseModel):
    subscription_id: str
    razorpay_key: str
    amount: int
    currency: str = "INR"


class UsageInfo(BaseModel):
    month: str
    memory_reads: int
    memory_writes: int
    storage_bytes: int
    monthly_ops_limit: Optional[int] = None
    storage_limit_bytes: Optional[int] = None
    plan: str
