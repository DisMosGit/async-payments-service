import asyncio
from dataclasses import dataclass

import httpx
import structlog

from async_payments_service.core.backoff import retry_delay
from async_payments_service.core.clock import Sleep
from async_payments_service.core.config import Settings
from async_payments_service.core.context import get_correlation_id
from async_payments_service.core.exceptions import WebhookDeliveryError
from async_payments_service.models.payment import Payment
from async_payments_service.schemas.webhooks import PaymentWebhookPayload

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class WebhookDelivery:
    status_code: int
    attempts: int


class WebhookSender:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        timeout: float,
        max_retries: int,
        base_delay: float,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._client = client
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._sleep = sleep

    async def send(self, payment: Payment) -> WebhookDelivery:
        body = PaymentWebhookPayload.from_payment(payment, get_correlation_id()).model_dump(mode="json")
        attempt = 0
        while True:
            status_code: int | None = None
            error: httpx.HTTPError | None = None
            try:
                response = await self._client.post(
                    payment.webhook_url,
                    json=body,
                    timeout=self._timeout,
                )
            except httpx.HTTPError as request_error:
                error = request_error
            else:
                status_code = response.status_code
                if response.is_success:
                    await logger.ainfo(
                        "webhook_delivered",
                        payment_id=str(payment.id),
                        attempts=attempt + 1,
                        status_code=status_code,
                    )
                    return WebhookDelivery(status_code=status_code, attempts=attempt + 1)

            if attempt >= self._max_retries:
                break
            delay = retry_delay(attempt, self._base_delay)
            await logger.awarning(
                "webhook_retry_scheduled",
                payment_id=str(payment.id),
                attempt=attempt + 1,
                max_retries=self._max_retries,
                delay=delay,
                status_code=status_code,
                error_type=type(error).__name__ if error is not None else None,
            )
            await self._sleep(delay)
            attempt += 1

        attempts = attempt + 1
        await logger.aerror(
            "webhook_delivery_failed",
            payment_id=str(payment.id),
            attempts=attempts,
            status_code=status_code,
            error_type=type(error).__name__ if error is not None else None,
        )
        raise WebhookDeliveryError(payment.id, attempts, status_code, error)


def create_webhook_sender(settings: Settings, client: httpx.AsyncClient) -> WebhookSender:
    return WebhookSender(
        client,
        timeout=settings.webhook_timeout,
        max_retries=settings.max_retries,
        base_delay=settings.retry_base_delay,
    )
