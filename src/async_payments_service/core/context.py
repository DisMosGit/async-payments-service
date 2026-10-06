import re
from uuid import uuid4

import structlog

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
MAX_ID_LENGTH = 128

_ID_PATTERN = re.compile(r"\A[A-Za-z0-9._:-]+\Z")


def new_request_id() -> str:
    return str(uuid4())


def sanitize_request_id(value: str | None) -> str | None:
    if value is None or not value or len(value) > MAX_ID_LENGTH:
        return None
    if _ID_PATTERN.match(value) is None:
        return None
    return value


def get_request_id() -> str | None:
    return _context_value("request_id")


def get_correlation_id() -> str | None:
    return _context_value("correlation_id")


def _context_value(key: str) -> str | None:
    value = structlog.contextvars.get_contextvars().get(key)
    return value if isinstance(value, str) else None
