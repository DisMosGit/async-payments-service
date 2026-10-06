from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from ulid import ULID

from async_payments_service.core.clock import utcnow
from async_payments_service.db.base import Base
from async_payments_service.models.enums import OutboxStatus
from async_payments_service.models.types import OUTBOX_STATUS_TYPE, ULID_TYPE, enum_check_constraint

EVENT_TYPE_LENGTH = 100


class OutboxEvent(Base):
    __tablename__ = "outbox"
    __table_args__ = (enum_check_constraint(OUTBOX_STATUS_TYPE, "status"),)

    id: Mapped[ULID] = mapped_column(ULID_TYPE, primary_key=True, default=ULID)
    aggregate_id: Mapped[ULID] = mapped_column(ULID_TYPE)
    event_type: Mapped[str] = mapped_column(sa.String(EVENT_TYPE_LENGTH))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[OutboxStatus] = mapped_column(OUTBOX_STATUS_TYPE, default=OutboxStatus.PENDING, index=True)
    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now(), index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(sa.Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
