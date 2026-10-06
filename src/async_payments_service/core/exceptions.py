from ulid import ULID

from async_payments_service.core.ids import IdempotencyKey


class PaymentNotFoundError(Exception):
    def __init__(self, payment_id: ULID) -> None:
        self.payment_id = payment_id
        super().__init__(f"payment {payment_id} was not found")


class DuplicateIdempotencyKeyError(Exception):
    def __init__(self, idempotency_key: IdempotencyKey) -> None:
        self.idempotency_key = idempotency_key
        super().__init__("idempotency key was already used with a different request")


class WebhookDeliveryError(Exception):
    def __init__(
        self,
        payment_id: ULID,
        attempts: int,
        status_code: int | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.payment_id = payment_id
        self.attempts = attempts
        self.status_code = status_code
        if cause is not None:
            self.__cause__ = cause
        super().__init__(f"webhook delivery failed for payment {payment_id} after {attempts} attempts")
