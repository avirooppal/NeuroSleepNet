import secrets
from typing import Tuple

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_api_key() -> Tuple[str, str, str]:
    """
    Returns (plaintext_key, hashed_key, prefix). Only plaintext shown once.
    Fix 1.4: Uses passlib pbkdf2_sha256 instead of fast SHA256.
    """
    raw = "nsn_live_" + secrets.token_urlsafe(32)
    hashed = pwd_context.hash(raw)
    prefix = raw[:16]  # Store prefix for display (nsn_live_xxxxxxxx)
    return raw, hashed, prefix


def verify_api_key(provided: str, stored_hash: str) -> bool:
    """
    Fix 1.4: Use passlib verify instead of raw SHA256 comparison.
    """
    try:
        return pwd_context.verify(provided, stored_hash)
    except ValueError:
        # passlib raises ValueError (or UnknownHashError) if hash format is invalid
        return False
