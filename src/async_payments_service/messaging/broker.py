from faststream.rabbit import RabbitBroker

from async_payments_service.core.config import Settings
from async_payments_service.messaging.retry import RetryMiddlewareFactory
from async_payments_service.messaging.types import BrokerHolder

PING_TIMEOUT = 5.0


def create_broker(settings: Settings) -> RabbitBroker:
    holder: BrokerHolder = BrokerHolder()
    broker: RabbitBroker = RabbitBroker(
        settings.rabbitmq_url,
        middlewares=(
            RetryMiddlewareFactory(holder.provider, settings.max_retries, settings.retry_base_delay),
        ),
    )
    holder.broker = broker
    return broker


async def ping_broker(broker: RabbitBroker) -> None:
    if not await broker.ping(timeout=PING_TIMEOUT):
        raise RuntimeError("broker is not connected")
