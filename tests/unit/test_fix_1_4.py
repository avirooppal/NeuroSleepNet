"""
Test Fix 1.4 — API key hashing uses passlib instead of SHA256.
"""
import pytest


def test_generate_api_key_uses_passlib():
    from distributed.backend.app.utils.crypto import generate_api_key

    raw, hashed, prefix = generate_api_key()
    assert raw.startswith("nsn_live_")
    assert len(prefix) == 16
    # passlib pbkdf2_sha256 hashes start with $pbkdf2-sha256$
    assert hashed.startswith("$pbkdf2-sha256$")


def test_verify_api_key_with_passlib():
    from distributed.backend.app.utils.crypto import generate_api_key, verify_api_key

    raw, hashed, _ = generate_api_key()
    assert verify_api_key(raw, hashed) is True
    assert verify_api_key("wrong-key", hashed) is False


def test_verify_api_key_fails_on_legacy_sha256():
    """
    passlib verify should fail on a raw SHA256 hex digest,
    because the hash format is unrecognised.
    """
    import hashlib
    from distributed.backend.app.utils.crypto import verify_api_key

    raw = "nsn_live_testkey123"
    sha256_hash = hashlib.sha256(raw.encode()).hexdigest()
    # passlib expects its own format; this should return False, not crash
    assert verify_api_key(raw, sha256_hash) is False
