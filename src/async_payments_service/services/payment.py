from typing import Any

import structlog
from pydantic import HttpUrl
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from ulid import ULID

from async_payments_service.core.context import get_correlation_id
from async_payments_service.core.exceptions import (
    DuplicateIdempotencyKeyError,
    PaymentNotFoundError,
)
from async_payments_service.core.ids import IdempotencyKey
from async_payments_service.models.enums import OutboxEventType, PaymentStatus
from async_payments_service.models.outbox import OutboxEvent
from async_payments_service.models.payment import Payment
from async_payments_service.repositories.unit_of_work import UnitOfWork
from async_payments_service.schemas.events import PaymentCreatedEvent
from async_payments_service.schemas.payments import PaymentCreateRequest

OUTBOX_EVENT_TYPE = OutboxEventType.PAYMENT_CREATED.code

logger = structlog.get_logger(__name__)


class PaymentService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_payment(self, request: PaymentCreateRequest, idempotency_key: IdempotencyKey) -> Payment:
        existing = await self._find_by_idempotency_key(idempotency_key)
        if existing is not None:
            return await self._replay(existing, request)

        try:
            payment = await self._create(request, idempotency_key)
        except IntegrityError:
            existing = await self._find_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return await self._replay(existing, request)

        await logger.ainfo("payment_created", payment_id=str(payment.id))
        return payment

    async def get_payment(self, payment_id: ULID) -> Payment:
        async with UnitOfWork(self._session_factory).transaction() as unit_of_work:
            payment = await unit_of_work.payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)
        return payment

    async def _create(self, request: PaymentCreateRequest, idempotency_key: IdempotencyKey) -> Payment:
        async with UnitOfWork(self._session_factory).transaction() as unit_of_work:
            payment = await unit_of_work.payments.add(
                Payment(
                    amount=request.amount,
                    currency=request.currency,
                    description=request.description,
                    payment_metadata=request.metadata,
                    status=PaymentStatus.PENDING,
                    idempotency_key=idempotency_key,
                    webhook_url=str(request.webhook_url),
                )
            )
            await unit_of_work.outbox.add(
                OutboxEvent(
                    aggregate_id=payment.id,
                    event_type=OUTBOX_EVENT_TYPE,
                    payload=_event_payload(payment),
                )
            )
        return payment

    async def _find_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Payment | None:
        async with UnitOfWork(self._session_factory).transaction() as unit_of_work:
            return await unit_of_work.payments.get_by_idempotency_key(idempotency_key)

    @staticmethod
    async def _replay(payment: Payment, request: PaymentCreateRequest) -> Payment:
        if not _matches(payment, request):
            raise DuplicateIdempotencyKeyError(payment.idempotency_key)
        await logger.ainfo("payment_replayed", payment_id=str(payment.id))
        return payment


def _matches(payment: Payment, request: PaymentCreateRequest) -> bool:
    return (
        payment.amount == request.amount
        and payment.currency == request.currency
        and payment.description == request.description
        and payment.payment_metadata == request.metadata
        and payment.webhook_url == str(request.webhook_url)
    )


def _event_payload(payment: Payment) -> dict[str, Any]:
    return _event(payment).model_dump(mode="json")


def _event(payment: Payment) -> PaymentCreatedEvent:
    return PaymentCreatedEvent(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        webhook_url=HttpUrl(payment.webhook_url),
        metadata=payment.payment_metadata,
        created_at=payment.created_at,
        correlation_id=get_correlation_id(),
    )
