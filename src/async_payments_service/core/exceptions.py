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
