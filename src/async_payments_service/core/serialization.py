from collections.abc import Callable
from typing import Any

import orjson

JSON_MEDIA_TYPE = "application/json"

JsonFallback = Callable[[Any], Any]


def dumps(value: Any) -> bytes:
    return orjson.dumps(value)


def dumps_text(value: Any, default: JsonFallback | None = None) -> str:
    return orjson.dumps(value, default=default).decode()


def loads(value: bytes | str) -> Any:
    return orjson.loads(value)
