from faststream.rabbit import RabbitBroker

from async_payments_service.core.config import Settings

PING_TIMEOUT = 5.0


def create_broker(settings: Settings) -> RabbitBroker:
    return RabbitBroker(settings.rabbitmq_url)


async def ping_broker(broker: RabbitBroker) -> None:
    if not await broker.ping(timeout=PING_TIMEOUT):
        raise RuntimeError("broker is not connected")
