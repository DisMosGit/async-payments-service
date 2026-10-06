import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncEngine

from async_payments_service.core.config import Settings, get_settings
from async_payments_service.db.engine import ping_database
from async_payments_service.messaging.broker import ping_broker

HEARTBEAT_STALE_FACTOR = 3.0

Probe = Callable[[], Awaitable[bool]]
WorkerRun = Callable[[], Awaitable[None]]


def heartbeat_path(settings: Settings) -> Path:
    return Path(settings.worker_heartbeat_file)


def heartbeat_max_age(settings: Settings) -> float:
    return settings.worker_heartbeat_interval * HEARTBEAT_STALE_FACTOR


def write_heartbeat(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def heartbeat_is_fresh(path: Path, max_age: float) -> bool:
    try:
        return time.time() - path.stat().st_mtime <= max_age
    except OSError:
        return False


def build_probe(engine: AsyncEngine, broker: RabbitBroker) -> Probe:
    async def probe() -> bool:
        try:
            await ping_database(engine)
            await ping_broker(broker)
        except Exception:
            return False
        return True

    return probe


async def beat(
    path: Path,
    interval: float,
    stop_event: asyncio.Event,
    probe: Probe | None = None,
) -> None:
    while not stop_event.is_set():
        if probe is None or await probe():
            write_heartbeat(path)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue


async def supervise(
    stop_event: asyncio.Event,
    path: Path,
    interval: float,
    probe: Probe,
    worker: WorkerRun,
) -> None:
    async with asyncio.TaskGroup() as group:
        group.create_task(beat(path, interval, stop_event, probe))
        group.create_task(run_until_stopped(worker, stop_event))


async def run_until_stopped(worker: WorkerRun, stop_event: asyncio.Event) -> None:
    try:
        await worker()
    finally:
        stop_event.set()


def main() -> None:
    settings = get_settings()
    path = heartbeat_path(settings)
    if not heartbeat_is_fresh(path, heartbeat_max_age(settings)):
        raise SystemExit(f"worker heartbeat is not fresh at {path}")
