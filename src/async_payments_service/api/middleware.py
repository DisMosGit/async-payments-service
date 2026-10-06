import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from async_payments_service.core.context import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    new_request_id,
    sanitize_request_id,
)


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = sanitize_request_id(headers.get(REQUEST_ID_HEADER)) or new_request_id()
        correlation_id = sanitize_request_id(headers.get(CORRELATION_ID_HEADER)) or request_id

        async def send_with_ids(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
                response_headers[CORRELATION_ID_HEADER] = correlation_id
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id, correlation_id=correlation_id):
            await self.app(scope, receive, send_with_ids)
