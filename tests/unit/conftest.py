import os
import pytest

# Set dummy environment variables for backend tests BEFORE any imports
os.environ["SECRET_KEY"] = "test_secret_key_at_least_32_characters_long"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["NSN_ENCRYPTION_MASTER_KEY"] = "test_encryption_key_32_characters_long"

@pytest.fixture(autouse=True)
def setup_test_env():
    yield
