import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class User(UserBase):
    id: uuid.UUID
    plan: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


class ApiKeyBase(BaseModel):
    name: Optional[str] = None


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKey(ApiKeyBase):
    id: uuid.UUID
    key_prefix: str
    last_used_at: Optional[datetime] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ApiKeyWithPlain(ApiKey):
    plaintext_key: str
