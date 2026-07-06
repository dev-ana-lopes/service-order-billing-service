# service-order-billing-service

FastAPI microservice responsible for quotes, approvals, payment preference creation, and payment status in the FIAP Phase 4 service-order system.

## Responsibility

This service owns quote and payment rules. It integrates with Mercado Pago through an infrastructure adapter and does not read OS or Execution databases.

## Architecture

- `src/domain`: quote, payment, money, status transitions, and domain events.
- `src/application`: use cases and ports for repositories, events, and payment gateways.
- `src/infrastructure`: settings, logging, repositories, fake gateway, Mercado Pago adapter, observability, and messaging adapters.
- `src/presentation`: FastAPI routes, request/response schemas, and HTTP dependencies.

Business rules stay away from HTTP clients, SDKs, queue clients, and framework details.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/billing/quotes` | Create a quote and publish `QUOTE_CREATED`. |
| `GET` | `/billing/quotes/{quote_id}` | Read a quote. |
| `POST` | `/billing/quotes/{quote_id}/approve` | Approve quote, create payment, and create checkout preference. |
| `GET` | `/billing/payments/{payment_id}` | Read a payment. |
| `POST` | `/billing/payments/{payment_id}/confirm` | Confirm payment and publish `PAYMENT_CONFIRMED`. |
| `POST` | `/billing/payments/{payment_id}/fail` | Fail payment and publish `PAYMENT_FAILED`. |
| `POST` | `/billing/payments/mercado-pago/webhook` | Map sandbox/demo Mercado Pago status to payment events. |
| `GET` | `/events` | List published in-memory events for demo/test evidence. |
| `POST` | `/events/drain` | Drain published in-memory events for demo/test evidence. |
| `GET` | `/health` | Health check. |
| `GET` | `/health/live` | Liveness check. |
| `GET` | `/health/ready` | Readiness check. |
| `GET` | `/metrics` | Prometheus-style metrics endpoint. |

Swagger is available at `/docs` when the app is running.

## Events

Published by this service:

- `QUOTE_CREATED`
- `QUOTE_APPROVED`
- `QUOTE_CANCELLED`
- `PAYMENT_PREFERENCE_CREATED`
- `PAYMENT_CONFIRMED`
- `PAYMENT_FAILED`

The event envelope is JSON with `event_id`, `event_type`, `correlation_id`, `occurred_at`, and `payload`.

## Runtime Mode

`APP_RUNTIME_MODE` controls infrastructure adapters:

- `memory`: uses in-memory repositories, in-memory publisher, and fake payment gateway.
- `real`: uses SQLAlchemy repositories, RabbitMQ publisher, and Mercado Pago Checkout Pro adapter.

## Mercado Pago

The application depends on `PaymentGatewayPort`. Infrastructure provides:

- `FakePaymentGateway` for unit tests and local deterministic flows.
- `MercadoPagoCheckoutAdapter` for Checkout Pro preference creation.

Required environment variables:

- `MERCADO_PAGO_ACCESS_TOKEN`
- `MERCADO_PAGO_ACCESS_TOKEN_FILE`
- `MERCADO_PAGO_API_BASE_URL`
- `MERCADO_PAGO_SUCCESS_URL`
- `MERCADO_PAGO_FAILURE_URL`
- `MERCADO_PAGO_PENDING_URL`

Access tokens must be provided through environment variables or Kubernetes secrets. They must never be committed or logged.

In `real` runtime mode, the app builds `MercadoPagoCheckoutAdapter` from environment variables and secret-backed settings.

The demo webhook endpoint accepts a payment id and a Mercado Pago status. `approved` and `accredited` confirm the payment; rejected/cancelled/refunded/charged back/expired statuses fail it; pending statuses leave it pending.

## Messaging

RabbitMQ integration is represented by thin infrastructure adapters:

- `RabbitMqEventPublisher`
- `RabbitMqEventConsumer`
- `RabbitMqBlockingEventWorker`

Automated tests use fake channels only. They do not connect to production queues. In `real` runtime mode, the app publishes events to RabbitMQ through `RabbitMqBlockingEventPublisher`.

The worker process runs with:

```bash
python -m src.worker
```

It consumes `OS_OPENED`, creates a default quote for the demo flow, publishes `QUOTE_CREATED`, and stores processed `event_id` values before acknowledging messages.

Environment variables:

- `RABBITMQ_URL`
- `RABBITMQ_EXCHANGE`
- `RABBITMQ_ROUTING_KEY`
- `RABBITMQ_QUEUE`
- `RABBITMQ_CONSUME_ROUTING_KEYS`
- `DEFAULT_QUOTE_ITEMS`
- `DEFAULT_QUOTE_AMOUNT`

## Database

The billing boundary has SQLAlchemy repositories for quotes and payments. `APP_RUNTIME_MODE=real` uses `DATABASE_URL`; `APP_RUNTIME_MODE=memory` keeps local in-memory repositories for tests.

Processed integration events are stored in `processed_events` for idempotent worker consumption.

## Local Development

```bash
uv sync --dev
make lint
make test
make test-cov
make run-dev
```

## Validation Evidence

Latest local validation for Phase 7:

- `uv run --dev black src tests`
- `uv run --dev isort src tests`
- `uv run --dev black --check src tests`
- `uv run --dev isort --check-only src tests`
- `uv run --dev flake8 src tests`
- `uv run --dev pytest --cov=src --cov-report=term-missing --cov-report=xml -q`

Result: `28 passed`, `89%` coverage.

## CI/CD and Deploy

The GitHub Actions workflow validates lint, tests, coverage, SonarCloud, image build/push to GHCR, manifest rendering, and k3s deployment.

Kubernetes manifests are under `k8s/`. Manifests must be rendered with an explicit GHCR image before applying to the cluster.

The API deployment is `k8s/deployment.yaml`; the RabbitMQ worker deployment is `k8s/deployment-worker.yaml`.

## Cost Notes

The target demo uses EC2 with k3s, GHCR images, RabbitMQ inside k3s, and shared low-cost infrastructure to stay within the AWS Academy budget.
