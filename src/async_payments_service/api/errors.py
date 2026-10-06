from collections.abc import Sequence
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from async_payments_service.core.exceptions import (
    DuplicateIdempotencyKeyError,
    PaymentNotFoundError,
)
from async_payments_service.schemas.errors import ErrorDetail, ErrorResponse

PAYMENT_NOT_FOUND_DETAIL = "Payment not found"
DUPLICATE_IDEMPOTENCY_KEY_DETAIL = "Idempotency key was already used with a different request"
INVALID_REQUEST_DETAIL = "Invalid request"


def error_response(status_code: int, detail: str, errors: Sequence[ErrorDetail] = ()) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(detail=detail, errors=list(errors)).model_dump(),
    )


async def payment_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(status.HTTP_404_NOT_FOUND, PAYMENT_NOT_FOUND_DETAIL)


async def duplicate_idempotency_key_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(status.HTTP_409_CONFLICT, DUPLICATE_IDEMPOTENCY_KEY_DETAIL)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    validation_error = cast(RequestValidationError, exc)
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        INVALID_REQUEST_DETAIL,
        validation_details(validation_error),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exception = cast(StarletteHTTPException, exc)
    return JSONResponse(
        status_code=http_exception.status_code,
        content=ErrorResponse(detail=str(http_exception.detail)).model_dump(),
        headers=http_exception.headers,
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
