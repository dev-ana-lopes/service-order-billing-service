from decimal import Decimal

from src.application.event_handlers import BillingIntegrationEventHandler
from src.domain.events import DomainEvent
from src.infrastructure.messaging.in_memory_event_publisher import InMemoryEventPublisher
from src.infrastructure.repositories.in_memory_billing_repositories import (
    InMemoryQuoteRepository,
)
from src.infrastructure.repositories.processed_event_repositories import (
    InMemoryProcessedEventRepository,
)


def test_billing_worker_handler_creates_default_quote_once() -> None:
    quote_repository = InMemoryQuoteRepository()
    publisher = InMemoryEventPublisher()
    processed_events = InMemoryProcessedEventRepository()
    message = DomainEvent(
        event_id="event-1",
        event_type="OS_OPENED",
        correlation_id="os-1",
        payload={"service_order_id": "os-1"},
    ).to_message()
    handler = BillingIntegrationEventHandler(
        quote_repository,
        publisher,
        processed_events,
        ["Initial diagnosis"],
        Decimal("120.00"),
    )

    first_result = handler.handle(message)
    second_result = handler.handle(message)

    quote = quote_repository.get_by_service_order_id("os-1")
    assert first_result == "processed"
    assert second_result == "skipped"
    assert quote.items == ["Initial diagnosis"]
    assert publisher.events[0].event_type == "QUOTE_CREATED"
