from collections.abc import Callable
from typing import Any, cast

import structlog
from faststream.message import StreamMessage
from faststream.message.utils import decode_message
from faststream.rabbit import RabbitBroker, RabbitMessage

from async_payments_service.messaging.retry import retry_count
from async_payments_service.messaging.topology import PAYMENTS_EXCHANGE, PAYMENTS_NEW_QUEUE
from async_payments_service.schemas.events import PaymentCreatedEvent
from async_payments_service.services.processing import PaymentProcessor
from async_payments_service.services.webhook import WebhookSender

logger = structlog.get_logger(__name__)

PaymentHandler = Callable[..., Any]


class PaymentConsumer:
    def __init__(self, processor: PaymentProcessor, sender: WebhookSender) -> None:
        self._processor = processor
        self._sender = sender

    async def handle(self, event: PaymentCreatedEvent, message: RabbitMessage) -> None:
        with structlog.contextvars.bound_contextvars(
            payment_id=str(event.payment_id),
            correlation_id=event.correlation_id,
        ):
            await logger.ainfo(
                "payment_event_received",
                payment_id=str(event.payment_id),
                correlation_id=event.correlation_id,
                amount=str(event.amount),
                currency=event.currency.code,
                attempt=retry_count(message),
            )
            payment = await self._processor.process_payment(event.payment_id)
            await self._sender.send(payment)


def decode_payment_event(message: StreamMessage[Any]) -> PaymentCreatedEvent:
    return PaymentCreatedEvent.model_validate(decode_message(message))


def declare_payment_consumer(broker: RabbitBroker, handler: PaymentHandler) -> RabbitBroker:
    broker.subscriber(
        PAYMENTS_NEW_QUEUE,
        exchange=PAYMENTS_EXCHANGE,
        decoder=decode_payment_event,
        title="payment.created",
    )(cast(Any, handler))
    return broker
