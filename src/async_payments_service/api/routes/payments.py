from fastapi import APIRouter, Depends, status

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
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentCreateResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
async def create_payment(
    payload: PaymentCreateRequest,
    idempotency_key: IdempotencyKeyDep,
    payment_service: PaymentServiceDep,
) -> PaymentCreateResponse:
    payment = await payment_service.create_payment(payload, idempotency_key)
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
