from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

StartupHook = Callable[[], Awaitable[None]]
ShutdownHook = Callable[[], Awaitable[None]]

logger = structlog.get_logger(__name__)


async def _run_startup_hooks(hooks: Sequence[StartupHook]) -> None:
    for hook in hooks:
        try:
            await hook()
        except Exception:
            await logger.aexception("application_startup_failed")
            raise


async def _run_shutdown_hooks(hooks: Sequence[ShutdownHook]) -> None:
    for hook in reversed(hooks):
        try:
            await hook()
        except Exception:
            await logger.aexception("shutdown_hook_failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await logger.ainfo("application_startup")
    try:
        await _run_startup_hooks(app.state.startup_hooks)
        yield
    finally:
        await logger.ainfo("application_shutdown_started")
        await _run_shutdown_hooks(app.state.shutdown_hooks)
        await logger.ainfo("application_shutdown_complete")
