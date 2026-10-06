from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] | None = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise RuntimeError("session factory is not configured")
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
