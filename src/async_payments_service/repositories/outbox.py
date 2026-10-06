from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from async_payments_service.models.enums import OutboxStatus
from async_payments_service.models.outbox import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> OutboxEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_pending(self, limit: int) -> list[OutboxEvent]:
        statement = (
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.PENDING)
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
