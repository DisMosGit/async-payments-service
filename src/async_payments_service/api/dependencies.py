import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from async_payments_service.core.config import get_settings

API_KEY_HEADER = "X-API-Key"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
MAX_IDEMPOTENCY_KEY_LENGTH = 255
IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9._:-]+$"


def require_api_key(x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None) -> str:
    expected = get_settings().api_key.get_secret_value()
    if x_api_key is None or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


def require_idempotency_key(
    idempotency_key: Annotated[
        str,
        Header(
            alias=IDEMPOTENCY_KEY_HEADER,
            min_length=1,
            max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
            pattern=IDEMPOTENCY_KEY_PATTERN,
        ),
    ],
) -> str:
    return idempotency_key


ApiKeyDep = Annotated[str, Depends(require_api_key)]
IdempotencyKeyDep = Annotated[str, Depends(require_idempotency_key)]
