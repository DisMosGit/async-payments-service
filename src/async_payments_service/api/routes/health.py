from typing import Literal

from fastapi import APIRouter, Request, Response, status

from async_payments_service.core.readiness import run_readiness_checks
from async_payments_service.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
async def ready(request: Request, response: Response) -> ReadyResponse:
    checks = await run_readiness_checks(request.app.state.readiness_checks)
    readiness: Literal["ready", "not_ready"] = "ready" if all(checks.values()) else "not_ready"
    if readiness != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status=readiness, checks=checks)
