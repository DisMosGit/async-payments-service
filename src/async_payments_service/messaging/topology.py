from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

PAYMENTS_EXCHANGE_NAME = "payments"
PAYMENTS_DLX_NAME = "payments.dlx"
PAYMENTS_NEW_QUEUE_NAME = "payments.new"
PAYMENTS_RETRY_QUEUE_NAME = "payments.retry"
PAYMENTS_DLQ_NAME = "payments.dlq"
PAYMENT_CREATED_ROUTING_KEY = "payments.new"
PAYMENT_DEAD_ROUTING_KEY = "payments.dead"
RETRY_COUNT_HEADER = "x-retry-count"

PAYMENTS_EXCHANGE = RabbitExchange(PAYMENTS_EXCHANGE_NAME, durable=True)
PAYMENTS_DLX = RabbitExchange(PAYMENTS_DLX_NAME, durable=True)
PAYMENTS_NEW_QUEUE = RabbitQueue(
    PAYMENTS_NEW_QUEUE_NAME,
    durable=True,
    routing_key=PAYMENT_CREATED_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX_NAME,
        "x-dead-letter-routing-key": PAYMENT_DEAD_ROUTING_KEY,
    },
)
PAYMENTS_RETRY_QUEUE = RabbitQueue(
    PAYMENTS_RETRY_QUEUE_NAME,
    durable=True,
    routing_key=PAYMENT_CREATED_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_EXCHANGE_NAME,
        "x-dead-letter-routing-key": PAYMENT_CREATED_ROUTING_KEY,
    },
)
PAYMENTS_DLQ = RabbitQueue(
    PAYMENTS_DLQ_NAME,
    durable=True,
    routing_key=PAYMENT_DEAD_ROUTING_KEY,
)


async def declare_broker_topology(broker: RabbitBroker) -> None:
    dlx = await broker.declare_exchange(PAYMENTS_DLX)
    exchange = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    dlq = await broker.declare_queue(PAYMENTS_DLQ)
    retry_queue = await broker.declare_queue(PAYMENTS_RETRY_QUEUE)
    new_queue = await broker.declare_queue(PAYMENTS_NEW_QUEUE)

    await dlq.bind(dlx, routing_key=PAYMENT_DEAD_ROUTING_KEY)
    await retry_queue.bind(exchange, routing_key=PAYMENT_CREATED_ROUTING_KEY)
    await new_queue.bind(exchange, routing_key=PAYMENT_CREATED_ROUTING_KEY)
