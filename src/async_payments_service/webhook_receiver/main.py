import random
from collections import deque
from decimal import Decimal
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, Request, Response
from ulid import ULID

from async_payments_service.core.clock import utcnow
from async_payments_service.core.logging import configure_logging
from async_payments_service.core.serialization import JSON_MEDIA_TYPE, dumps, loads
from async_payments_service.models.enums import Currency, PaymentStatus
from async_payments_service.schemas.webhooks import PaymentWebhookPayload

HOST = "0.0.0.0"
PORT = 9000
RECEIVED_LIMIT = 100
FAILURE_PREFIX = "fail"
SUCCESS_STATUS = 200
FAILURE_STATUS = 500

logger = structlog.get_logger(__name__)

app = FastAPI(title="webhook receiver")

received: deque[dict[str, Any]] = deque(maxlen=RECEIVED_LIMIT)


def read_payload(body: bytes) -> Any:
    try:
        return loads(body)
    except ValueError:
        return body.decode(errors="replace")


def record(path: str, source: str, payload: Any, response_status: int) -> None:
    received.append(
        {
            "received_at": utcnow().isoformat(),
            "path": path,
            "source": source,
            "response_status": response_status,
            "payload": payload,
        }
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/received")
async def list_received() -> dict[str, Any]:
    return {"count": len(received), "received": list(reversed(received))}


@app.delete("/received", status_code=204)
async def clear_received() -> None:
    received.clear()


@app.post("/generate")
async def generate() -> dict[str, Any]:
    status = random.choice([PaymentStatus.SUCCEEDED, PaymentStatus.FAILED])
    payload = PaymentWebhookPayload(
        event=f"payment.{status.code}",
        payment_id=ULID(),
        status=status,
        amount=Decimal(random.randrange(1, 100_000)) / 100,
        currency=random.choice(list(Currency)),
        metadata={"order_id": f"ord-{random.randrange(1 << 24):06x}"},
        processed_at=utcnow(),
        correlation_id=str(ULID()),
    ).model_dump(mode="json")
    record("/generate", "generated", payload, SUCCESS_STATUS)
    return payload


@app.post("/{path:path}")
async def receive(path: str, request: Request) -> Response:
    payload = read_payload(await request.body())
    response_status = FAILURE_STATUS if path.split("/", 1)[0] == FAILURE_PREFIX else SUCCESS_STATUS
    record(path, "webhook", payload, response_status)
    await logger.ainfo(
        "webhook_received",
        path=path,
        status_code=response_status,
        payment_id=payload.get("payment_id") if isinstance(payload, dict) else None,
        correlation_id=payload.get("correlation_id") if isinstance(payload, dict) else None,
    )
    return Response(
        content=dumps({"status": "received"}),
        status_code=response_status,
        media_type=JSON_MEDIA_TYPE,
    )


def main() -> None:
    configure_logging()
    uvicorn.run(app, host=HOST, port=PORT, log_config=None)
