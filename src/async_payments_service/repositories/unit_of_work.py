from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from async_payments_service.db.transaction import transaction
from async_payments_service.repositories.outbox import OutboxRepository
from async_payments_service.repositories.payment import PaymentRepository


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session

    @property
    def payments(self) -> PaymentRepository:
        return PaymentRepository(self.session)

    @property
    def outbox(self) -> OutboxRepository:
        return OutboxRepository(self.session)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[UnitOfWork]:
        async with self._session_factory() as session, transaction(session):
            self._session = session
            try:
                yield self
            finally:
                self._session = None
