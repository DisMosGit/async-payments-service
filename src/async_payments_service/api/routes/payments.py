from fastapi import APIRouter, Depends, Response, status

from async_payments_service.api.dependencies import (
    IdempotencyKeyDep,
    PaymentServiceDep,
    require_api_key,
)
from async_payments_service.schemas.errors import ErrorResponse
from async_payments_service.schemas.ids import UlidField
from async_payments_service.schemas.payments import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentDetailResponse,
)

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentCreateResponse,
    responses={
        status.HTTP_200_OK: {"model": PaymentCreateResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
async def create_payment(
    payload: PaymentCreateRequest,
    response: Response,
    idempotency_key: IdempotencyKeyDep,
    payment_service: PaymentServiceDep,
) -> PaymentCreateResponse:
    payment, created = await payment_service.create_payment(payload, idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return PaymentCreateResponse.from_payment(payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
async def get_payment(payment_id: UlidField, payment_service: PaymentServiceDep) -> PaymentDetailResponse:
    payment = await payment_service.get_payment(payment_id)
    return PaymentDetailResponse.from_payment(payment)
