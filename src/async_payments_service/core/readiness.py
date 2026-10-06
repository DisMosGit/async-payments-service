from collections.abc import Awaitable, Callable, Mapping

import structlog

ReadinessCheck = Callable[[], Awaitable[None]]

logger = structlog.get_logger(__name__)


async def run_readiness_checks(checks: Mapping[str, ReadinessCheck]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name, check in checks.items():
        try:
            await check()
        except Exception:
            results[name] = False
            await logger.aexception("readiness_check_failed", check=name)
        else:
            results[name] = True
    return results
