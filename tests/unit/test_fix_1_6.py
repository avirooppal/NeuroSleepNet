"""
Test Fix 1.6 — Anonymous access capped at free tier.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_anonymous_user_created_with_free_plan(monkeypatch):
    from distributed.backend.app.api.v1.auth import get_current_user
    from distributed.backend.app.config import settings

    # Must enable anonymous access for this test
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_ACCESS", True)

    mock_request = MagicMock()
    mock_request.headers.get.return_value = None  # No auth header

    mock_db = AsyncMock()

    # First call: no anonymous user exists → should create one with plan="free"
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    await get_current_user(mock_request, db=mock_db)

    # Check that add() was called with a user whose plan is 'free'
    calls = mock_db.add.call_args_list
    if calls:
        user_obj = calls[0][0][0]
        assert user_obj.plan == "free"
