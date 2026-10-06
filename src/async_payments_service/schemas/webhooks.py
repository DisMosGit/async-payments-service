from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, field_validator

from async_payments_service.models.enums import PaymentStatus
from async_payments_service.models.payment import Payment
from async_payments_service.schemas.enums import CurrencyField, PaymentStatusField
from async_payments_service.schemas.ids import UlidField

TERMINAL_STATUSES = (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED)


class PaymentWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event: str
    payment_id: UlidField
    status: PaymentStatusField
    amount: Decimal
    currency: CurrencyField
    metadata: dict[str, Any]
    processed_at: datetime | None
    correlation_id: str | None = None

    @field_validator("status")
    @classmethod
    def validate_terminal_status(cls, value: PaymentStatus) -> PaymentStatus:
        if value not in TERMINAL_STATUSES:
            raise ValueError("webhooks are sent only for terminal payment statuses")
        return value

    @classmethod
    def from_payment(cls, payment: Payment, correlation_id: str | None = None) -> Self:
        return cls(
            event=f"payment.{payment.status.code}",
            payment_id=payment.id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            metadata=payment.payment_metadata,
            processed_at=payment.processed_at,
            correlation_id=correlation_id,
        )
