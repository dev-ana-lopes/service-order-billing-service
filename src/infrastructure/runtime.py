from __future__ import annotations

from src.infrastructure.config.settings import Settings
from src.infrastructure.database.readiness import DatabaseReadinessProbe
from src.infrastructure.database.url_utils import validate_runtime_database_url
from src.infrastructure.messaging.in_memory_event_publisher import InMemoryEventPublisher
from src.infrastructure.messaging.rabbitmq_blocking_publisher import (
    RabbitMqBlockingEventPublisher,
)
from src.infrastructure.messaging.rabbitmq_blocking_worker import (
    RabbitMqBlockingEventWorker,
)
from src.infrastructure.payment.fake_payment_gateway import FakePaymentGateway
from src.infrastructure.payment.mercado_pago_checkout_adapter import (
    MercadoPagoCheckoutAdapter,
    MercadoPagoCheckoutSettings,
)
from src.infrastructure.repositories.in_memory_billing_repositories import (
    InMemoryPaymentRepository,
    InMemoryQuoteRepository,
)
from src.infrastructure.repositories.processed_event_repositories import (
    InMemoryProcessedEventRepository,
    SqlAlchemyProcessedEventRepository,
)
from src.infrastructure.repositories.sqlalchemy_billing_repositories import (
    SqlAlchemyPaymentRepository,
    SqlAlchemyQuoteRepository,
)


def build_quote_repository(settings: Settings):
    if settings.APP_RUNTIME_MODE == "real":
        return SqlAlchemyQuoteRepository(settings.DATABASE_URL)
    return InMemoryQuoteRepository()


def build_database_readiness_probe(settings: Settings):
    if settings.APP_RUNTIME_MODE != "real":
        return None

    validate_runtime_database_url(
        settings.DATABASE_URL,
        expected_database=settings.EXPECTED_DATABASE_NAME,
        expected_username=settings.EXPECTED_DATABASE_USERNAME,
    )
    return DatabaseReadinessProbe(
        settings.DATABASE_URL,
        expected_database=settings.EXPECTED_DATABASE_NAME,
        expected_username=settings.EXPECTED_DATABASE_USERNAME,
        timeout_seconds=settings.HEALTHCHECK_TIMEOUT_SECONDS,
    )


def build_payment_repository(settings: Settings):
    if settings.APP_RUNTIME_MODE == "real":
        return SqlAlchemyPaymentRepository(settings.DATABASE_URL)
    return InMemoryPaymentRepository()


def build_event_publisher(settings: Settings):
    if settings.APP_RUNTIME_MODE == "real":
        return RabbitMqBlockingEventPublisher(
            settings.RABBITMQ_URL,
            settings.RABBITMQ_EXCHANGE,
            settings.RABBITMQ_ROUTING_KEY,
            settings.RABBITMQ_QUEUE,
        )
    return InMemoryEventPublisher()


def build_payment_gateway(settings: Settings):
    if settings.PAYMENT_PROVIDER_MODE == "mercado_pago":
        return MercadoPagoCheckoutAdapter(
            MercadoPagoCheckoutSettings(
                access_token=settings.MERCADO_PAGO_ACCESS_TOKEN,
                success_url=settings.MERCADO_PAGO_SUCCESS_URL,
                failure_url=settings.MERCADO_PAGO_FAILURE_URL,
                pending_url=settings.MERCADO_PAGO_PENDING_URL,
                timeout_seconds=settings.MERCADO_PAGO_REQUEST_TIMEOUT_SECONDS,
            )
        )
    return FakePaymentGateway()


def build_processed_event_repository(settings: Settings):
    if settings.APP_RUNTIME_MODE == "real":
        return SqlAlchemyProcessedEventRepository(settings.DATABASE_URL)
    return InMemoryProcessedEventRepository()


def build_event_worker(settings: Settings, handler):
    return RabbitMqBlockingEventWorker(
        settings.RABBITMQ_URL,
        settings.RABBITMQ_EXCHANGE,
        settings.RABBITMQ_QUEUE,
        settings.RABBITMQ_CONSUME_ROUTING_KEYS,
        handler,
    )
