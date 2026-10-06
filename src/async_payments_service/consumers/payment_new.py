from collections.abc import Callable
from typing import Any, cast

import structlog
from faststream.message import StreamMessage
from faststream.message.utils import decode_message
from faststream.rabbit import RabbitBroker, RabbitMessage

from async_payments_service.messaging.retry import retry_count
from async_payments_service.messaging.topology import PAYMENTS_EXCHANGE, PAYMENTS_NEW_QUEUE
from async_payments_service.schemas.events import PaymentCreatedEvent

logger = structlog.get_logger(__name__)

PaymentHandler = Callable[..., Any]


def decode_payment_event(message: StreamMessage[Any]) -> PaymentCreatedEvent:
    return PaymentCreatedEvent.model_validate(decode_message(message))


async def handle_payment_new(event: PaymentCreatedEvent, message: RabbitMessage) -> None:
    await logger.ainfo(
        "payment_event_received",
        payment_id=str(event.payment_id),
        correlation_id=event.correlation_id,
        amount=str(event.amount),
        currency=event.currency.code,
        attempt=retry_count(message),
    )


def declare_payment_consumer(
    broker: RabbitBroker, handler: PaymentHandler = handle_payment_new
) -> RabbitBroker:
    broker.subscriber(
        PAYMENTS_NEW_QUEUE,
        exchange=PAYMENTS_EXCHANGE,
        decoder=decode_payment_event,
        title="payment.created",
    )(cast(Any, handler))
    return broker
