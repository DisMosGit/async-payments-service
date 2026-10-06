import enum


class SerializableEnum(enum.IntEnum):
    @property
    def code(self) -> str:
        return self.name


class Currency(SerializableEnum):
    USD = 1
    EUR = 2
    GBP = 3
    RUB = 4


class PaymentStatus(SerializableEnum):
    PENDING = 1
    PROCESSING = 2
    SUCCEEDED = 3
    FAILED = 4

    @property
    def code(self) -> str:
        return self.name.lower()


class OutboxStatus(SerializableEnum):
    PENDING = 1
    PUBLISHED = 2
    FAILED = 3

    @property
    def code(self) -> str:
        return self.name.lower()


class OutboxEventType(SerializableEnum):
    PAYMENT_CREATED = 1

    @property
    def code(self) -> str:
        return self.name.lower().replace("_", ".")
