from types import TracebackType
from typing import Any, cast

import structlog
from faststream._internal.basic_types import AsyncFuncAny
from faststream._internal.middlewares import BaseMiddleware
from faststream.rabbit.message import RabbitMessage

from async_payments_service.core.backoff import retry_delay
from async_payments_service.core.serialization import loads
from async_payments_service.messaging.topology import PAYMENTS_RETRY_QUEUE, RETRY_COUNT_HEADER
from async_payments_service.messaging.types import RabbitBrokerProvider
from async_payments_service.schemas.events import PaymentCreatedEvent

logger = structlog.get_logger(__name__)


class RetryMiddlewareFactory:
    def __init__(
        self,
        broker_provider: RabbitBrokerProvider,
        max_retries: int,
        base_delay: float,
    ) -> None:
        self.broker_provider = broker_provider
        self.max_retries = max_retries
        self.base_delay = base_delay

    def __call__(self, msg: Any, *, context: Any) -> RetryMiddleware:
        return RetryMiddleware(msg, context=context, factory=self)


class RetryMiddleware(BaseMiddleware[Any, Any]):
    def __init__(self, msg: Any, *, context: Any, factory: RetryMiddlewareFactory) -> None:
        super().__init__(msg, context=context)
        self.factory = factory

    async def consume_scope(self, call_next: AsyncFuncAny, msg: Any) -> Any:
        return await call_next(msg)

    async def after_processed(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool | None:
        if exc_val is None or not isinstance(exc_val, Exception):
            return False

        message = cast("RabbitMessage", self.msg)
        attempt = retry_count(message)
        payload = retry_payload(message.body)
        if payload is None or attempt >= self.factory.max_retries:
            await logger.aerror(
                "payment_event_retry_exhausted",
                attempt=attempt,
                max_retries=self.factory.max_retries,
                error=repr(exc_val),
            )
            return False

        await self.factory.broker_provider().publish(
            payload,
            queue=PAYMENTS_RETRY_QUEUE,
            headers={**message.headers, RETRY_COUNT_HEADER: attempt + 1},
            expiration=retry_delay(attempt, self.factory.base_delay),
            persist=True,
        )
        await logger.awarning(
            "payment_event_retry_scheduled",
            attempt=attempt + 1,
            max_retries=self.factory.max_retries,
            error=repr(exc_val),
        )
        return True


def retry_count(message: RabbitMessage) -> int:
    value = message.headers.get(RETRY_COUNT_HEADER)
    return value if isinstance(value, int) else 0


def retry_payload(body: Any) -> dict[str, Any] | None:
    payload = decode_body(body)
    if payload is None:
        return None
    try:
        PaymentCreatedEvent.model_validate(payload)
    except ValueError:
        return None
    return payload


def decode_body(body: Any) -> dict[str, Any] | None:
    if isinstance(body, dict):
        return body
    if isinstance(body, bytes):
        try:
            decoded = loads(body)
        except ValueError:
            return None
        return decoded if isinstance(decoded, dict) else None
    return None
