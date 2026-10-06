from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OUTBOX_TABLE = "outbox"
NEXT_ATTEMPT_AT_COLUMN = "next_attempt_at"


def upgrade() -> None:
    op.add_column(
        OUTBOX_TABLE,
        sa.Column(NEXT_ATTEMPT_AT_COLUMN, sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(OUTBOX_TABLE, NEXT_ATTEMPT_AT_COLUMN)
