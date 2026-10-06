import enum
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ulid import ULID

from async_payments_service.models.enums import Currency, OutboxStatus, PaymentStatus


class IntEnumType[E: enum.IntEnum](sa.TypeDecorator[E]):
    impl = sa.SmallInteger
    cache_ok = True

    enum_class: type[E]
    name: str

    def __init__(self, enum_class: type[E], name: str) -> None:
        super().__init__()
        self.enum_class = enum_class
        self.name = name

    def process_bind_param(self, value: E | None, dialect: sa.Dialect) -> int | None:
        if value is None:
            return None
        return int(self.enum_class(value))

    def process_result_value(self, value: Any, dialect: sa.Dialect) -> E | None:
        if value is None:
            return None
        return self.enum_class(value)


def enum_check_constraint[E: enum.IntEnum](column_type: IntEnumType[E], column: str) -> sa.CheckConstraint:
    codes = ", ".join(str(member.value) for member in column_type.enum_class)
    return sa.CheckConstraint(f"{column} IN ({codes})", name=column_type.name)


class UlidType(sa.TypeDecorator[ULID]):
    impl = PG_UUID
    cache_ok = True

    def process_bind_param(self, value: ULID | None, dialect: sa.Dialect) -> UUID | None:
        if value is None:
            return None
        return value.to_uuid()

    def process_result_value(self, value: Any, dialect: sa.Dialect) -> ULID | None:
        if value is None:
            return None
        return ULID.from_uuid(value)


CURRENCY_TYPE = IntEnumType(Currency, "currency")
PAYMENT_STATUS_TYPE = IntEnumType(PaymentStatus, "payment_status")
OUTBOX_STATUS_TYPE = IntEnumType(OutboxStatus, "outbox_status")
ULID_TYPE = UlidType()
