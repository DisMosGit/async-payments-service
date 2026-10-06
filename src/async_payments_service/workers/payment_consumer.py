import asyncio

import httpx
import structlog
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from async_payments_service.consumers.payment_new import PaymentConsumer, declare_payment_consumer
from async_payments_service.core.config import Settings, get_settings
from async_payments_service.core.logging import configure_logging
from async_payments_service.core.signals import build_stop_event
from async_payments_service.db.engine import create_engine
from async_payments_service.db.session import create_session_factory
from async_payments_service.messaging.broker import create_broker
from async_payments_service.messaging.topology import declare_broker_topology
from async_payments_service.services.processing import create_payment_processor
from async_payments_service.services.webhook import create_webhook_sender
from async_payments_service.workers.heartbeat import build_probe, heartbeat_path, supervise

logger = structlog.get_logger(__name__)


def create_consumer(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    client: httpx.AsyncClient,
) -> PaymentConsumer:
    return PaymentConsumer(
        create_payment_processor(settings, session_factory),
        create_webhook_sender(settings, client),
    )


async def consume(broker: RabbitBroker, consumer: PaymentConsumer, stop_event: asyncio.Event) -> None:
    await declare_broker_topology(broker)
    declare_payment_consumer(broker, consumer.handle)
    await broker.start()
    await logger.ainfo("payment_consumer_started")
    try:
        await stop_event.wait()
    finally:
        await logger.ainfo("payment_consumer_stopped")


async def serve(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    engine: AsyncEngine,
    client: httpx.AsyncClient,
    stop_event: asyncio.Event,
) -> None:
    consumer = create_consumer(settings, session_factory, client)
    try:
        await supervise(
            stop_event,
            heartbeat_path(settings),
            settings.worker_heartbeat_interval,
            build_probe(engine, broker),
            lambda: consume(broker, consumer, stop_event),
        )
    finally:
        await broker.stop()
        await client.aclose()
        await engine.dispose()


async def run(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    engine: AsyncEngine,
    client: httpx.AsyncClient,
) -> None:
    stop_event = build_stop_event()
    await broker.connect()
    await serve(settings, session_factory, broker, engine, client, stop_event)


def main() -> None:
    configure_logging()
    settings = get_settings()
    engine = create_engine(settings)
    broker = create_broker(settings)
    client = httpx.AsyncClient()
    asyncio.run(run(settings, create_session_factory(engine), broker, engine, client))
