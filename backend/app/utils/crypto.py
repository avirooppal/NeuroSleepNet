import hashlib
import secrets
from typing import Tuple

from passlib.context import CryptContext

from ..config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_api_key() -> Tuple[str, str, str]:
    """Returns (plaintext_key, hashed_key, prefix). Only plaintext shown once."""
    raw = "nsn_live_" + secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:16]  # Store prefix for display (nsn_live_xxxxxxxx)
    return raw, hashed, prefix


def verify_api_key(provided: str, stored_hash: str) -> bool:
    provided_hash = hashlib.sha256(provided.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, stored_hash)
