from typing import Annotated, Any
from uuid import UUID

from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema
from ulid import ULID

from async_payments_service.core.ids import IdempotencyKey

ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"
ULID_SCHEMA: dict[str, Any] = {"type": "string", "pattern": ULID_PATTERN}
IDEMPOTENCY_KEY_SCHEMA: dict[str, Any] = {
    "type": "string",
    "description": "A ULID or an RFC 4122 UUID; responses always carry the ULID form",
}


def parse_ulid(value: Any) -> Any:
    if isinstance(value, ULID):
        return value
    if isinstance(value, str):
        try:
            return ULID.from_str(value.upper())
        except ValueError as error:
            raise ValueError("input should be a ULID") from error
    return value


def parse_idempotency_key(value: Any) -> Any:
    if isinstance(value, ULID):
        return value
    if isinstance(value, str):
        try:
            return ULID.from_str(value.upper())
        except ValueError:
            pass
        try:
            return ULID.from_uuid(UUID(value))
        except ValueError as error:
            raise ValueError("input should be a ULID or a UUID") from error
    return value


def ulid_to_str(value: ULID) -> str:
    return str(value)


UlidField = Annotated[
    ULID,
    BeforeValidator(parse_ulid),
    PlainSerializer(ulid_to_str, return_type=str),
    WithJsonSchema(ULID_SCHEMA, mode="validation"),
    WithJsonSchema(ULID_SCHEMA, mode="serialization"),
]

IdempotencyKeyField = Annotated[
    IdempotencyKey,
    BeforeValidator(parse_idempotency_key),
    PlainSerializer(ulid_to_str, return_type=str),
    WithJsonSchema(IDEMPOTENCY_KEY_SCHEMA, mode="validation"),
    WithJsonSchema(IDEMPOTENCY_KEY_SCHEMA, mode="serialization"),
]
