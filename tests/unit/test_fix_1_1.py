"""
Test Fix 1.1 — Hardcoded secrets removal.
"""
import os
import sys
import tempfile
import json

import pytest


def test_config_rejects_placeholder_secret_key():
    """SECRET_KEY must not use a known placeholder."""
    from distributed.backend.app.config import Settings

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        Settings(SECRET_KEY="your_super_secret_key_here", POSTGRES_PASSWORD="valid_pass_123")

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        Settings(SECRET_KEY="changeme", POSTGRES_PASSWORD="valid_pass_123")

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        Settings(SECRET_KEY="", POSTGRES_PASSWORD="valid_pass_123")


def test_config_rejects_placeholder_postgres_password():
    """POSTGRES_PASSWORD must not use a known placeholder."""
    from distributed.backend.app.config import Settings

    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD is not set"):
        Settings(SECRET_KEY="a_valid_secret_key_here_1234567890", POSTGRES_PASSWORD="postgres")

    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD is not set"):
        Settings(SECRET_KEY="a_valid_secret_key_here_1234567890", POSTGRES_PASSWORD="password")

    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD is not set"):
        Settings(SECRET_KEY="a_valid_secret_key_here_1234567890", POSTGRES_PASSWORD="")


def test_config_accepts_valid_secrets():
    """Valid secrets should instantiate without error."""
    from distributed.backend.app.config import Settings

    s = Settings(
        SECRET_KEY="a_valid_secret_key_here_1234567890",
        POSTGRES_PASSWORD="my_strong_password_123",
    )
    assert s.SECRET_KEY == "a_valid_secret_key_here_1234567890"
    assert s.POSTGRES_PASSWORD == "my_strong_password_123"


def test_cli_generates_and_persists_local_api_key(monkeypatch):
    """CLI must generate a random local API key on first use and persist it."""
    import neurosleepnet.cli as cli

    with tempfile.TemporaryDirectory() as tmpdir:
        creds_file = os.path.join(tmpdir, "credentials")
        monkeypatch.setattr(cli, "_CREDENTIALS_FILE", creds_file)
        monkeypatch.setattr(cli, "_CREDENTIALS_DIR", tmpdir)

        key1 = cli._get_local_api_key()
        assert key1.startswith("nsn_local_")
        assert len(key1) > 40

        # Second call must return the same key (idempotent)
        key2 = cli._get_local_api_key()
        assert key1 == key2

        # File must be readable JSON
        with open(creds_file, "r") as f:
            data = json.load(f)
        assert data["local_api_key"] == key1
