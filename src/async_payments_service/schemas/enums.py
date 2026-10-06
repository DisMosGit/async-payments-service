from functools import partial
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema

from async_payments_service.models.enums import Currency, PaymentStatus, SerializableEnum


def enum_from_code[E: SerializableEnum](enum_class: type[E], value: Any) -> E:
    if isinstance(value, enum_class):
        return value
    if isinstance(value, str):
        for member in enum_class:
            if member.code == value:
                return member
    raise ValueError(f"input should be one of {', '.join(member.code for member in enum_class)}")


def enum_to_code(value: SerializableEnum) -> str:
    return value.code


def code_schema[E: SerializableEnum](enum_class: type[E]) -> dict[str, Any]:
    return {"type": "string", "enum": [member.code for member in enum_class]}


CURRENCY_CODE_SCHEMA = code_schema(Currency)
PAYMENT_STATUS_CODE_SCHEMA = code_schema(PaymentStatus)

CurrencyField = Annotated[
    Currency,
    BeforeValidator(partial(enum_from_code, Currency)),
    PlainSerializer(enum_to_code, return_type=str),
    WithJsonSchema(CURRENCY_CODE_SCHEMA, mode="validation"),
    WithJsonSchema(CURRENCY_CODE_SCHEMA, mode="serialization"),
]

PaymentStatusField = Annotated[
    PaymentStatus,
    BeforeValidator(partial(enum_from_code, PaymentStatus)),
    PlainSerializer(enum_to_code, return_type=str),
    WithJsonSchema(PAYMENT_STATUS_CODE_SCHEMA, mode="validation"),
    WithJsonSchema(PAYMENT_STATUS_CODE_SCHEMA, mode="serialization"),
]
