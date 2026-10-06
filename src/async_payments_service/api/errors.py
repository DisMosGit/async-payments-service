from collections.abc import Mapping, Sequence
from typing import Any, cast

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from async_payments_service.core.exceptions import (
    DuplicateIdempotencyKeyError,
    PaymentNotFoundError,
)
from async_payments_service.core.serialization import JSON_MEDIA_TYPE, dumps
from async_payments_service.schemas.errors import ErrorDetail, ErrorResponse

PAYMENT_NOT_FOUND_DETAIL = "Payment not found"
DUPLICATE_IDEMPOTENCY_KEY_DETAIL = "Idempotency key was already used with a different request"
INVALID_REQUEST_DETAIL = "Invalid request"


def json_response(
    status_code: int,
    content: Mapping[str, Any],
    headers: Mapping[str, str] | None = None,
) -> Response:
    return Response(
        content=dumps(dict(content)),
        status_code=status_code,
        media_type=JSON_MEDIA_TYPE,
        headers=headers,
    )


def error_response(status_code: int, detail: str, errors: Sequence[ErrorDetail] = ()) -> Response:
    content = ErrorResponse(detail=detail, errors=list(errors)).model_dump(mode="json")
    return json_response(status_code, content)


async def payment_not_found_handler(request: Request, exc: Exception) -> Response:
    return error_response(status.HTTP_404_NOT_FOUND, PAYMENT_NOT_FOUND_DETAIL)


async def duplicate_idempotency_key_handler(request: Request, exc: Exception) -> Response:
    return error_response(status.HTTP_409_CONFLICT, DUPLICATE_IDEMPOTENCY_KEY_DETAIL)


async def validation_error_handler(request: Request, exc: Exception) -> Response:
    validation_error = cast(RequestValidationError, exc)
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        INVALID_REQUEST_DETAIL,
        validation_details(validation_error),
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    http_exception = cast(StarletteHTTPException, exc)
    return json_response(
        http_exception.status_code,
        ErrorResponse(detail=str(http_exception.detail)).model_dump(mode="json"),
        http_exception.headers,
    )


def validation_details(exc: RequestValidationError) -> list[ErrorDetail]:
    return [
        ErrorDetail(
            location=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
            type=error["type"],
        )
        for error in exc.errors()
    ]


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PaymentNotFoundError, payment_not_found_handler)
    app.add_exception_handler(DuplicateIdempotencyKeyError, duplicate_idempotency_key_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
