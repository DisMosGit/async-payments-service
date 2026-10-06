from typing import NewType

from ulid import ULID

IdempotencyKey = NewType("IdempotencyKey", ULID)
