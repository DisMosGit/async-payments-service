from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from async_payments_service.core.ids import IdempotencyKey
from async_payments_service.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.flush()
        return payment

    async def get_by_id(self, payment_id: ULID) -> Payment | None:
        return await self._session.get(Payment, payment_id)

    async def get_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Payment | None:
        statement = select(Payment).where(Payment.idempotency_key == idempotency_key)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
