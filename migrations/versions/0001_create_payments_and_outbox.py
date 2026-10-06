from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from async_payments_service.models.types import (
    CURRENCY_TYPE,
    OUTBOX_STATUS_TYPE,
    PAYMENT_STATUS_TYPE,
    ULID_TYPE,
    enum_check_constraint,
)

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYMENTS_TABLE = "payments"
OUTBOX_TABLE = "outbox"
IDEMPOTENCY_INDEX = "ix_payments_idempotency_key"
OUTBOX_STATUS_INDEX = "ix_outbox_status"
OUTBOX_CREATED_AT_INDEX = "ix_outbox_created_at"


def upgrade() -> None:
    op.create_table(
        PAYMENTS_TABLE,
        sa.Column("id", ULID_TYPE, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", CURRENCY_TYPE, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", PAYMENT_STATUS_TYPE, nullable=False),
        sa.Column("idempotency_key", ULID_TYPE, nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        enum_check_constraint(CURRENCY_TYPE, "currency"),
        enum_check_constraint(PAYMENT_STATUS_TYPE, "status"),
    )
    op.create_index(IDEMPOTENCY_INDEX, PAYMENTS_TABLE, ["idempotency_key"], unique=True)
    op.create_table(
        OUTBOX_TABLE,
        sa.Column("id", ULID_TYPE, nullable=False),
        sa.Column("aggregate_id", ULID_TYPE, nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", OUTBOX_STATUS_TYPE, nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbox"),
        enum_check_constraint(OUTBOX_STATUS_TYPE, "status"),
    )
    op.create_index(OUTBOX_STATUS_INDEX, OUTBOX_TABLE, ["status"])
    op.create_index(OUTBOX_CREATED_AT_INDEX, OUTBOX_TABLE, ["created_at"])


def downgrade() -> None:
    op.drop_index(OUTBOX_CREATED_AT_INDEX, table_name=OUTBOX_TABLE)
    op.drop_index(OUTBOX_STATUS_INDEX, table_name=OUTBOX_TABLE)
    op.drop_table(OUTBOX_TABLE)
    op.drop_index(IDEMPOTENCY_INDEX, table_name=PAYMENTS_TABLE)
    op.drop_table(PAYMENTS_TABLE)
