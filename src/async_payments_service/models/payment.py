from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from ulid import ULID

from async_payments_service.core.clock import utcnow
from async_payments_service.core.ids import IdempotencyKey
from async_payments_service.db.base import Base
from async_payments_service.models.enums import Currency, PaymentStatus
from async_payments_service.models.types import (
    CURRENCY_TYPE,
    PAYMENT_STATUS_TYPE,
    ULID_TYPE,
    enum_check_constraint,
)

PAYMENT_METADATA_COLUMN = "metadata"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        enum_check_constraint(CURRENCY_TYPE, "currency"),
        enum_check_constraint(PAYMENT_STATUS_TYPE, "status"),
    )

    id: Mapped[ULID] = mapped_column(ULID_TYPE, primary_key=True, default=ULID)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 2))
    currency: Mapped[Currency] = mapped_column(CURRENCY_TYPE)
    description: Mapped[str | None] = mapped_column(sa.Text)
    payment_metadata: Mapped[dict[str, Any]] = mapped_column(PAYMENT_METADATA_COLUMN, JSONB, default=dict)
    status: Mapped[PaymentStatus] = mapped_column(PAYMENT_STATUS_TYPE, default=PaymentStatus.PENDING)
    idempotency_key: Mapped[IdempotencyKey] = mapped_column(ULID_TYPE, unique=True, index=True)
    webhook_url: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
