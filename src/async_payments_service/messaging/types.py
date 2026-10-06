from collections.abc import Callable

from faststream.rabbit import RabbitBroker

RabbitBrokerProvider = Callable[[], RabbitBroker]


class BrokerHolder:
    def __init__(self) -> None:
        self._broker: RabbitBroker | None = None

    @property
    def broker(self) -> RabbitBroker:
        if self._broker is None:
            raise RuntimeError("broker is not configured")
        return self._broker

    @broker.setter
    def broker(self, broker: RabbitBroker) -> None:
        self._broker = broker

    def provider(self) -> RabbitBroker:
        return self.broker
