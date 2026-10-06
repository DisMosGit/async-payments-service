import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from async_payments_service.core.config import get_settings
from async_payments_service.core.ids import IdempotencyKey
from async_payments_service.schemas.ids import IdempotencyKeyField
from async_payments_service.services.payment import PaymentService

API_KEY_HEADER = "X-API-Key"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def require_api_key(x_api_key: Annotated[str | None, Security(api_key_header)] = None) -> str:
    expected = get_settings().api_key.get_secret_value()
    if x_api_key is None or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


def require_idempotency_key(
    idempotency_key: Annotated[IdempotencyKeyField, Header(alias=IDEMPOTENCY_KEY_HEADER)],
) -> IdempotencyKey:
    return idempotency_key


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] | None = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise RuntimeError("session factory is not configured")
    return factory


def get_payment_service(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> PaymentService:
    return PaymentService(session_factory)


ApiKeyDep = Annotated[str, Depends(require_api_key)]
IdempotencyKeyDep = Annotated[IdempotencyKey, Depends(require_idempotency_key)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
