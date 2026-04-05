from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class NeuroSleepNetError(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class AuthenticationError(NeuroSleepNetError):
    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(
            status_code=status_code.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(NeuroSleepNetError):
    def __init__(self, detail: str = "Not enough permissions") -> None:
        super().__init__(status_code=status_code.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(NeuroSleepNetError):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=status_code.HTTP_404_NOT_FOUND, detail=detail)


class PlanLimitError(NeuroSleepNetError):
    def __init__(self, detail: str, upgrade_url: str = "https://neurosleepnet.com/upgrade") -> None:
        super().__init__(
            status_code=status_code.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": detail, "upgrade_url": upgrade_url},
        )


class RateLimitError(NeuroSleepNetError):
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60) -> None:
        super().__init__(
            status_code=status_code.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": detail, "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )


class DatabaseUnavailableError(NeuroSleepNetError):
    def __init__(self, detail: str = "Database service is currently unavailable") -> None:
        super().__init__(
            status_code=status_code.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            headers={"Retry-After": "30"},
        )


class EmbeddingUnavailableError(NeuroSleepNetError):
    def __init__(self, detail: str = "Both embedding providers failed") -> None:
        super().__init__(status_code=status_code.HTTP_502_BAD_GATEWAY, detail=detail)
