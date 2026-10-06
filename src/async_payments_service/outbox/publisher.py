from typing import Any

from faststream.rabbit import RabbitBroker

from async_payments_service.messaging.topology import (
    PAYMENT_CREATED_ROUTING_KEY,
    PAYMENTS_EXCHANGE,
)
from async_payments_service.schemas.events import PaymentCreatedEvent


async def publish_payment_created(broker: RabbitBroker, event: PaymentCreatedEvent) -> None:
    kwargs: dict[str, Any] = {}
    if event.correlation_id is not None:
        kwargs["correlation_id"] = event.correlation_id
    await broker.publish(
        event,
        exchange=PAYMENTS_EXCHANGE,
        routing_key=PAYMENT_CREATED_ROUTING_KEY,
        content_type="application/json",
        persist=True,
        **kwargs,
    )
