"""
AES-256-GCM content encryption with HKDF per-tenant key derivation.

Memory `content` is encrypted before writing to Postgres. Embedding vectors
are stored unencrypted (they are mathematical representations — not readable).
Per-tenant keys are derived from NSN_ENCRYPTION_MASTER_KEY + tenant_id so
that a leaked row cannot be decrypted without the master key.
"""
import os
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.warning(
        "[NSN Crypto] 'cryptography' package not installed. "
        "Content will be stored unencrypted. Install with: pip install cryptography"
    )

# Sentinel prefixes so we can detect encrypted vs. plaintext records during migration
_ENC_PREFIX_V1 = "nsn:enc:v1:"
_ENC_PREFIX_V2 = "nsn:enc:v2:"
_SALT_SIZE = 16   # 128-bit salt for HKDF
_NONCE_SIZE = 12  # 96-bit nonce for AES-GCM


def _get_master_key() -> Optional[bytes]:
    """Load and validate the master encryption key from environment."""
    raw = os.environ.get("NSN_ENCRYPTION_MASTER_KEY", "")
    if not raw:
        return None
    return raw.encode("utf-8")


def derive_key(tenant_id: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit AES key for a specific tenant using HKDF.
    Same master key + different tenant_id + different salt = completely different derived key.
    Fix 1.5: salt is now cryptographically random per-encryption, not None.
    """
    master = _get_master_key()
    if not master or not _CRYPTO_AVAILABLE:
        return b""

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=f"nsn-tenant:{tenant_id}".encode("utf-8"),
    )
    return hkdf.derive(master)


def encrypt_content(content: str, tenant_id: str) -> str:
    """
    Encrypt content string with AES-256-GCM.
    Returns a base64-encoded string with prefix so callers can detect encryption.
    Falls back to plaintext if crypto is unavailable (logs warning once).
    Fix 1.5: Embeds a random HKDF salt in the payload (v2 format).
    """
    if not _CRYPTO_AVAILABLE or not _get_master_key():
        return content  # Graceful degradation — never crash the write path

    salt = os.urandom(_SALT_SIZE)
    key = derive_key(tenant_id, salt)
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, content.encode("utf-8"), None)

    # Pack salt + nonce + ciphertext → base64 → v2 prefix
    packed = base64.b64encode(salt + nonce + ciphertext).decode("utf-8")
    return f"{_ENC_PREFIX_V2}{packed}"


def decrypt_content(stored: str, tenant_id: str) -> str:
    """
    Decrypt a content string previously encrypted by encrypt_content().
    Supports v2 (salted HKDF) and v1 (salt=None legacy).
    If the string doesn't carry an encryption prefix (legacy plaintext record),
    it is returned as-is — safe migration path.
    """
    if not stored.startswith(_ENC_PREFIX_V2) and not stored.startswith(_ENC_PREFIX_V1):
        return stored  # Plaintext legacy record — return unchanged

    if not _CRYPTO_AVAILABLE or not _get_master_key():
        logger.error("[NSN Crypto] Cannot decrypt — 'cryptography' package missing or no master key.")
        return "[DECRYPTION UNAVAILABLE]"

    if stored.startswith(_ENC_PREFIX_V2):
        prefix_len = len(_ENC_PREFIX_V2)
        packed = base64.b64decode(stored[prefix_len:])
        salt = packed[:_SALT_SIZE]
        nonce = packed[_SALT_SIZE:_SALT_SIZE + _NONCE_SIZE]
        ciphertext = packed[_SALT_SIZE + _NONCE_SIZE:]
        key = derive_key(tenant_id, salt)
    else:
        # v1 legacy: salt was None
        prefix_len = len(_ENC_PREFIX_V1)
        packed = base64.b64decode(stored[prefix_len:])
        nonce = packed[:_NONCE_SIZE]
        ciphertext = packed[_NONCE_SIZE:]
        key = derive_key(tenant_id, b"")

    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.error(f"[NSN Crypto] Decryption failed for tenant {tenant_id}: {e}")
        return "[DECRYPTION FAILED]"


def is_encrypted(content: str) -> bool:
    """Returns True if content was encrypted by this module."""
    return content.startswith(_ENC_PREFIX_V2) or content.startswith(_ENC_PREFIX_V1)
