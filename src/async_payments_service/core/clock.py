from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]
Sleep = Callable[[float], Awaitable[None]]


def utcnow() -> datetime:
    return datetime.now(UTC)
