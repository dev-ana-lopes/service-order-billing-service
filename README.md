# service-order-billing-service

FastAPI microservice responsible for quotes, approvals, payment preference creation, and payment status in the FIAP Phase 4 service-order system.

## Responsibility

This service owns quote and payment rules. It integrates with Mercado Pago through an infrastructure adapter, does not read OS or Execution databases, and must run against its own PostgreSQL database/user pair.

## Architecture

The complete Phase 4 architecture, Saga strategy, service boundaries, databases, communication and technology rationale is documented in [docs/architecture/fase4-final.md](docs/architecture/fase4-final.md).

- `src/domain`: quote, payment, money, status transitions, and domain events.
- `src/application`: use cases and ports for repositories, events, and payment gateways.
- `src/infrastructure`: settings, logging, repositories, fake gateway, Mercado Pago adapter, observability, and messaging adapters.
- `src/presentation`: FastAPI routes, request/response schemas, and HTTP dependencies.

Business rules stay away from HTTP clients, SDKs, queue clients, and framework details.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/quotes` | Create a quote and publish `QUOTE_CREATED`. |
| `GET` | `/quotes/{quote_id}` | Read a quote. |
| `GET` | `/quotes/by-service-order/{service_order_id}` | Read the quote generated for a service order. |
| `POST` | `/quotes/{quote_id}/approve` | Approve quote, create payment, and create checkout preference. |
| `GET` | `/payments/{payment_id}` | Read a payment. |
| `GET` | `/payments/by-service-order/{service_order_id}` | Read the payment generated for a service order. |
| `POST` | `/payments/{payment_id}/sync` | Query Mercado Pago and reconcile the payment status without a webhook. |
| `POST` | `/payments/{payment_id}/confirm` | Confirm payment and publish `PAYMENT_CONFIRMED`. |
| `POST` | `/payments/{payment_id}/fail` | Fail payment and publish `PAYMENT_FAILED`. |
| `POST` | `/internal/test/payments/{payment_id}/simulate` | Simulate approved/pending/rejected/failure transitions when internal test endpoints are enabled. |
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

`APP_RUNTIME_MODE` controls persistence and messaging adapters:

- `memory`: uses in-memory repositories and in-memory publisher.
- `real`: uses SQLAlchemy repositories and RabbitMQ publisher.

`PAYMENT_PROVIDER_MODE` controls the payment provider adapter:

- `mock`: keeps the deterministic fake gateway and is the default for local deterministic flows.
- `mercado_pago`: enables the Mercado Pago Checkout Pro adapter and on-demand payment reconciliation.

## Mercado Pago

The application depends on `PaymentGatewayPort`. Infrastructure provides:

- `FakePaymentGateway` for unit tests and local deterministic flows.
- `MercadoPagoSdkClient` for the official Mercado Pago Python SDK.
- `MercadoPagoCheckoutAdapter` for Checkout Pro preference creation and payment sync.

Required environment variables:

- `MERCADO_PAGO_ACCESS_TOKEN`
- `MERCADO_PAGO_ACCESS_TOKEN_FILE`
- `MERCADO_PAGO_SUCCESS_URL`
- `MERCADO_PAGO_FAILURE_URL`
- `MERCADO_PAGO_PENDING_URL`
- `MERCADO_PAGO_REQUEST_TIMEOUT_SECONDS`
- `ENABLE_INTERNAL_TEST_ENDPOINTS`

Access tokens must be provided through environment variables or Kubernetes secrets. They must never be committed or logged.
When `PAYMENT_PROVIDER_MODE=mercado_pago`, the official `mercadopago` Python SDK uses the Mercado Pago API and requires a valid sandbox or production access token. The local `local-demo-token` is not valid in this mode.

In Mercado Pago mode, the adapter uses `X-Idempotency-Key` for preference creation and returns the hosted checkout URL. Use `POST /payments/{payment_id}/sync` to query `GET /v1/payments/search` by `external_reference`; the adapter validates the payment reference, amount, currency and uniqueness before publishing a transition. This integration does not use a webhook. `POST /payments/{payment_id}/confirm` and `/fail` remain restricted operational/test controls.

For local-only flows, keep `PAYMENT_PROVIDER_MODE=mock` and enable `ENABLE_INTERNAL_TEST_ENDPOINTS=true` to use `POST /internal/test/payments/{payment_id}/simulate`.

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

The default Billing service ownership contract is:

- database: `billing_service_db`
- user: `billing_service_user`

`/health/ready` validates both connectivity and ownership by checking the connected database name and user against `EXPECTED_DATABASE_NAME` and `EXPECTED_DATABASE_USERNAME`.

Processed integration events are stored in `processed_events` for idempotent worker consumption.

Alembic migrations live under `alembic/` and remain the canonical schema management path for explicit migration jobs. Repository adapters still call `metadata.create_all` as a defensive bootstrap for local and test flows.

## Local Development

```bash
uv sync --dev
make lint
make test
make test-cov
make run-dev
```

The local API defaults to `http://localhost:8002` and Swagger to `http://localhost:8002/docs`.

## Local Docker Stack

The default `docker compose up --build` stack includes:

- `migrate`
- `api`
- `worker`
- `postgres`
- `mailhog`

Useful local URLs:

- API: `http://localhost:8002`
- Swagger: `http://localhost:8002/docs`
- RabbitMQ management: `http://localhost:15672`
- MailHog: `http://localhost:8026`

Notes:

- `docker compose up` forces `APP_RUNTIME_MODE=real`, even if `.env` still says `memory`.
- The local Docker stack expects the shared RabbitMQ broker to already be running on `amqp://guest:guest@localhost:5672/%2F`, typically from `service-order-os-service`.
- The local stack uses `PAYMENT_PROVIDER_MODE=mock` for deterministic quote approval without a live sandbox token.
- Database migrations run through the dedicated `migrate` service before the API and worker start.

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
