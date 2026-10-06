from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from async_payments_service.models.payment import Payment
from async_payments_service.schemas.enums import CurrencyField, PaymentStatusField
from async_payments_service.schemas.ids import IdempotencyKeyField, UlidField

DESCRIPTION_MAX_LENGTH = 1000


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: CurrencyField
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl


class PaymentCreateResponse(BaseModel):
    id: UlidField
    status: PaymentStatusField
    amount: Decimal
    currency: CurrencyField
    idempotency_key: IdempotencyKeyField
    created_at: datetime

    @classmethod
    def from_payment(cls, payment: Payment) -> Self:
        return cls(
            id=payment.id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            idempotency_key=payment.idempotency_key,
            created_at=payment.created_at,
        )


class PaymentDetailResponse(PaymentCreateResponse):
    description: str | None
    metadata: dict[str, Any]
    webhook_url: str
    processed_at: datetime | None

    @classmethod
    def from_payment(cls, payment: Payment) -> Self:
        return cls(
            id=payment.id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            idempotency_key=payment.idempotency_key,
            created_at=payment.created_at,
            description=payment.description,
            metadata=payment.payment_metadata,
            webhook_url=payment.webhook_url,
            processed_at=payment.processed_at,
        )
