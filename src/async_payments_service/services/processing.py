import asyncio
import random
from dataclasses import dataclass, field
from typing import Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from ulid import ULID

from async_payments_service.core.clock import Clock, Sleep, utcnow
from async_payments_service.core.config import Settings
from async_payments_service.core.exceptions import PaymentNotFoundError
from async_payments_service.models.enums import PaymentStatus
from async_payments_service.models.payment import Payment
from async_payments_service.repositories.unit_of_work import UnitOfWork

TERMINAL_STATUSES = frozenset({PaymentStatus.SUCCEEDED, PaymentStatus.FAILED})

logger = structlog.get_logger(__name__)


class PaymentGateway(Protocol):
    async def charge(self, payment: Payment) -> bool: ...


@dataclass(frozen=True)
class EmulatedGateway:
    min_delay: float
    max_delay: float
    success_rate: float
    sleep: Sleep = asyncio.sleep
    rng: random.Random = field(default_factory=random.Random)

    async def charge(self, payment: Payment) -> bool:
        await self.sleep(self.rng.uniform(self.min_delay, self.max_delay))
        return self.rng.random() < self.success_rate


class PaymentProcessor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        gateway: PaymentGateway,
        *,
        clock: Clock = utcnow,
    ) -> None:
        self._session_factory = session_factory
        self._gateway = gateway
        self._clock = clock

    async def process_payment(self, payment_id: ULID) -> Payment:
        payment = await self._load(payment_id)
        if payment.status in TERMINAL_STATUSES:
            await logger.ainfo(
                "payment_already_processed",
                payment_id=str(payment.id),
                status=payment.status.code,
            )
            return payment
        succeeded = await self._gateway.charge(payment)
        return await self._store_outcome(payment.id, succeeded)

    async def _load(self, payment_id: ULID) -> Payment:
        async with UnitOfWork(self._session_factory).transaction() as unit_of_work:
            payment = await unit_of_work.payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)
        return payment

    async def _store_outcome(self, payment_id: ULID, succeeded: bool) -> Payment:
        async with UnitOfWork(self._session_factory).transaction() as unit_of_work:
            payment = await unit_of_work.payments.get_by_id(payment_id)
            if payment is None:
                raise PaymentNotFoundError(payment_id)
            payment.status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
            payment.processed_at = self._clock()
        await logger.ainfo(
            "payment_processed",
            payment_id=str(payment.id),
            status=payment.status.code,
        )
        return payment


def create_payment_processor(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> PaymentProcessor:
    return PaymentProcessor(
        session_factory,
        EmulatedGateway(
            min_delay=settings.gateway_min_delay,
            max_delay=settings.gateway_max_delay,
            success_rate=settings.gateway_success_rate,
        ),
    )
