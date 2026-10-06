from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, HttpUrl

from async_payments_service.schemas.enums import CurrencyField
from async_payments_service.schemas.ids import UlidField


class PaymentCreatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payment_id: UlidField
    amount: Decimal
    currency: CurrencyField
    webhook_url: HttpUrl
    metadata: dict[str, Any]
    created_at: datetime
    correlation_id: str | None = None
