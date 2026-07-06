from decimal import Decimal

from src.domain.payment import Money, Payment, Quote
from src.infrastructure.repositories.processed_event_repositories import (
    SqlAlchemyProcessedEventRepository,
)
from src.infrastructure.repositories.sqlalchemy_billing_repositories import (
    SqlAlchemyPaymentRepository,
    SqlAlchemyQuoteRepository,
)


def test_sqlalchemy_quote_repository_saves_and_restores_quote() -> None:
    repository = SqlAlchemyQuoteRepository("sqlite+pysqlite:///:memory:")
    quote, _ = Quote.create("os-1", ["Brake pads"], Money(Decimal("120.00")))
    quote.approve()

    repository.save(quote)
    restored = repository.get_by_service_order_id("os-1")

    assert restored.quote_id == quote.quote_id
    assert restored.status == quote.status
    assert restored.items == ["Brake pads"]


def test_sqlalchemy_payment_repository_saves_and_restores_payment() -> None:
    repository = SqlAlchemyPaymentRepository("sqlite+pysqlite:///:memory:")
    quote, _ = Quote.create("os-1", ["Brake pads"], Money(Decimal("120.00")))
    quote.approve()
    payment = Payment.from_quote(quote)

    repository.save(payment)
    restored = repository.get(payment.payment_id)

    assert restored.payment_id == payment.payment_id
    assert restored.quote_id == quote.quote_id
    assert restored.status == payment.status


def test_sqlalchemy_processed_event_repository_tracks_processed_events() -> None:
    repository = SqlAlchemyProcessedEventRepository("sqlite+pysqlite:///:memory:")

    assert repository.is_processed("event-1") is False

    repository.mark_processed("event-1", "OS_OPENED", "os-1")
    repository.mark_processed("event-1", "OS_OPENED", "os-1")

    assert repository.is_processed("event-1") is True
