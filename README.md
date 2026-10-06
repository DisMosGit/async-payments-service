# Асинхронный сервис процессинга платежей

Принимает запросы на оплату, обрабатывает их через эмуляцию платёжного шлюза и отправляет результат на webhook.

## Запуск

```bash
docker compose up --build -d
```

Поднимаются `postgres`, `rabbitmq`, `api`, `consumer`, `outbox-publisher` и `webhook-receiver`; миграции применяются при старте `api`. Готовность:

```bash
docker compose ps
```

- API — http://localhost:8000, Swagger UI — http://localhost:8000/docs
- RabbitMQ — http://localhost:15672, логин и пароль `guest`
- Webhook-заглушка — http://localhost:9000, принятые уведомления — http://localhost:9000/received
- API-ключ из `docker-compose.yml` — `dev-api-key`

Остановить: `docker compose down`, вместе с данными — `docker compose down -v`. Те же команды есть в Makefile: `make docker-up` и `make docker-down`.

## Примеры

Все запросы к API требуют заголовок `X-API-Key`.

### Создание платежа

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: dev-api-key' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 01M487S7705D0NSN2NKQYH304N' \
  -d '{
    "amount": "149.90",
    "currency": "EUR",
    "description": "Подписка на 3 месяца",
    "metadata": {"order_id": "ord-4af19c", "source": "mobile"},
    "webhook_url": "http://webhook-receiver:9000/hooks/payments"
  }'
```

Ответ `202 Accepted`:

```json
{
  "payment_id": "01M487S770EW54MS0GJA402XMG",
  "status": "pending",
  "amount": "149.90",
  "currency": "EUR",
  "idempotency_key": "01M487S7705D0NSN2NKQYH304N",
  "created_at": "2026-10-06T09:12:44.512004Z"
}
```

`webhook_url` ведёт на заглушку `webhook-receiver` — так она называется внутри сети compose.

`Idempotency-Key` — ULID или UUID. Повторный запрос с тем же ключом и тем же телом вернёт тот же платёж и снова `202`; тот же ключ с другим телом — `409 Conflict`. Без заголовка — `422`, без верного `X-API-Key` — `401`.

### Получение платежа

```bash
curl -H 'X-API-Key: dev-api-key' http://localhost:8000/api/v1/payments/01M41H3SM8XC0MZYSAYGJPP877
```

Ответ `200 OK`; до обработки статус `pending`, после — `succeeded` или `failed`:

```json
{
  "payment_id": "01M41H3SM8XC0MZYSAYGJPP877",
  "status": "succeeded",
  "amount": "75.00",
  "currency": "USD",
  "idempotency_key": "01M41H3SM8H7PQFA3BS0J0YDMW",
  "created_at": "2026-10-03T18:41:07.208773Z",
  "description": "Доплата за доставку",
  "metadata": {"order_id": "ord-90be27"},
  "webhook_url": "http://webhook-receiver:9000/hooks/shop",
  "processed_at": "2026-10-03T18:41:11.604219Z"
}
```

### Уведомление на webhook

После обработки на `webhook_url` уходит POST с телом:

```json
{
  "event": "payment.succeeded",
  "payment_id": "01M45FGTXMB614SBX546JB89Y5",
  "status": "succeeded",
  "amount": "3120.00",
  "currency": "RUB",
  "metadata": {"order_id": "ord-c31d8a"},
  "processed_at": "2026-10-05T07:30:18.442876Z",
  "correlation_id": "01M45FGY6A8H9B5P6C4K9G6EZT"
}
```

Принятые уведомления — http://localhost:9000/received (новые первыми, хранятся в памяти). `curl -X POST http://localhost:9000/generate` вернёт пример уведомления. Если путь в `webhook_url` начинается с `/fail/`, заглушка отвечает `500` — так проверяются повторные попытки и DLQ.
