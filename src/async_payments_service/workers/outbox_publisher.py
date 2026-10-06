import asyncio
import signal
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from faststream.rabbit import RabbitBroker
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from async_payments_service.core.clock import utcnow
from async_payments_service.core.config import Settings, get_settings
from async_payments_service.core.logging import configure_logging
from async_payments_service.db.engine import create_engine
from async_payments_service.db.session import create_session_factory
from async_payments_service.db.transaction import transaction
from async_payments_service.messaging.broker import create_broker
from async_payments_service.messaging.topology import declare_broker_topology
from async_payments_service.models.enums import OutboxEventType, OutboxStatus
from async_payments_service.models.outbox import OutboxEvent
from async_payments_service.outbox.publisher import publish_payment_created, retry_interval
from async_payments_service.repositories.outbox import OutboxRepository
from async_payments_service.schemas.events import PaymentCreatedEvent

OUTBOX_EVENT_TYPE = OutboxEventType.PAYMENT_CREATED.code
MAX_ERROR_LENGTH = 500

logger = structlog.get_logger(__name__)


class EventUnpublishableError(ValueError):
    pass


def describe_error(error: BaseException) -> str:
    message = repr(error)
    return message if len(message) <= MAX_ERROR_LENGTH else f"{message[:MAX_ERROR_LENGTH]}..."


@dataclass(frozen=True)
class Cycle:
    claimed: int = 0
    published: int = 0
    retried: int = 0
    failed: int = 0
    next_deadline: float | None = None


class OutboxPublisher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        broker: RabbitBroker,
        *,
        batch_size: int,
        max_retries: int,
        base_delay: float,
        poll_interval: float,
    ) -> None:
        self._session_factory = session_factory
        self._broker = broker
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._poll_interval = poll_interval

    async def publish_batch(self) -> Cycle:
        now = utcnow()
        published = retried = failed = 0
        next_deadline: float | None = None

        async with self._session_factory() as session, transaction(session):
            events = await OutboxRepository(session).claim_pending(self._batch_size, now)
            for event in events:
                if await self._publish(event, now):
                    published += 1
                    continue
                retry_scheduled, deadline = self._settle_failure(event, now)
                if retry_scheduled:
                    retried += 1
                else:
                    failed += 1
                if deadline is not None:
                    next_deadline = deadline if next_deadline is None else min(next_deadline, deadline)

        cycle = Cycle(
            claimed=len(events),
            published=published,
            retried=retried,
            failed=failed,
            next_deadline=next_deadline,
        )
        if cycle.claimed:
            await logger.ainfo(
                "outbox_batch_published",
                claimed=cycle.claimed,
                published=cycle.published,
                retried=cycle.retried,
                failed=cycle.failed,
            )
        return cycle

    async def run(self, stop_event: asyncio.Event) -> None:
        loop = asyncio.get_running_loop()
        while not stop_event.is_set():
            cycle = await self.publish_batch()
            timeout = self._poll_interval
            if cycle.next_deadline is not None:
                timeout = min(timeout, max(cycle.next_deadline - loop.time(), 0.0))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=timeout)
            except TimeoutError:
                continue

    async def _publish(self, event: OutboxEvent, now: datetime) -> bool:
        try:
            await publish_payment_created(self._broker, self._event(event))
        except (EventUnpublishableError, ValidationError) as error:
            event.last_error = describe_error(error)
            event.status = OutboxStatus.FAILED
            await logger.aerror(
                "outbox_event_unpublishable",
                event_id=str(event.id),
                event_type=event.event_type,
                error=describe_error(error),
            )
            return False
        except Exception as error:
            event.last_error = describe_error(error)
            await logger.aerror(
                "outbox_publish_failed",
                event_id=str(event.id),
                event_type=event.event_type,
                error=describe_error(error),
            )
            return False

        event.status = OutboxStatus.PUBLISHED
        event.published_at = now
        event.next_attempt_at = None
        await logger.ainfo(
            "outbox_event_published",
            event_id=str(event.id),
            payment_id=str(event.aggregate_id),
            event_type=event.event_type,
        )
        return True

    def _settle_failure(self, event: OutboxEvent, now: datetime) -> tuple[bool, float | None]:
        if event.status is OutboxStatus.FAILED:
            return False, None
        event.retry_count += 1
        event.last_error = f"attempt {event.retry_count}: {event.last_error}"
        if event.retry_count > self._max_retries:
            event.status = OutboxStatus.FAILED
            return False, None
        delay = retry_interval(event.retry_count, self._base_delay)
        event.next_attempt_at = now + timedelta(seconds=delay)
        return True, asyncio.get_running_loop().time() + delay

    def _event(self, event: OutboxEvent) -> PaymentCreatedEvent:
        if event.event_type != OUTBOX_EVENT_TYPE:
            raise EventUnpublishableError(f"unsupported event type {event.event_type!r}")
        return PaymentCreatedEvent.model_validate(event.payload)


def create_outbox_publisher(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
) -> OutboxPublisher:
    return OutboxPublisher(
        session_factory,
        broker,
        batch_size=settings.outbox_batch_size,
        max_retries=settings.max_retries,
        base_delay=settings.retry_base_delay,
        poll_interval=settings.outbox_poll_interval,
    )


async def run_forever(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    stop_event: asyncio.Event,
) -> None:
    await declare_broker_topology(broker)
    publisher = create_outbox_publisher(settings, session_factory, broker)
    await logger.ainfo("outbox_publisher_started", poll_interval=settings.outbox_poll_interval)
    try:
        await publisher.run(stop_event)
    except Exception:
        await logger.aexception("outbox_publisher_failed")
        raise
    finally:
        await logger.ainfo("outbox_publisher_stopped")


def build_stop_event() -> asyncio.Event:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop_event.set)
    return stop_event


async def serve(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    engine: AsyncEngine,
    stop_event: asyncio.Event,
) -> None:
    try:
        await run_forever(settings, session_factory, broker, stop_event)
    finally:
        await broker.stop()
        await engine.dispose()


async def run(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    engine: AsyncEngine,
) -> None:
    stop_event = build_stop_event()
    await broker.connect()
    await serve(settings, session_factory, broker, engine, stop_event)


def main() -> None:
    configure_logging()
    settings = get_settings()
    engine = create_engine(settings)
    broker = create_broker(settings)
    asyncio.run(run(settings, create_session_factory(engine), broker, engine))
