from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.application.ports import (
    EventPublisherPort,
    ProcessedEventRepositoryPort,
    QuoteRepositoryPort,
)
from src.application.use_cases import CreateQuoteCommand, CreateQuoteUseCase


class BillingIntegrationEventHandler:
    def __init__(
        self,
        quote_repository: QuoteRepositoryPort,
        publisher: EventPublisherPort,
        processed_events: ProcessedEventRepositoryPort,
        default_items: list[str],
        default_amount: Decimal,
    ) -> None:
        self._quote_repository = quote_repository
        self._publisher = publisher
        self._processed_events = processed_events
        self._default_items = default_items
        self._default_amount = default_amount

    def handle(self, message: dict[str, Any]) -> str:
        event_id = str(message["event_id"])
        event_type = str(message["event_type"])
        correlation_id = str(message["correlation_id"])
        if self._processed_events.is_processed(event_id):
            return "skipped"
        if event_type != "OS_OPENED":
            return "ignored"

        payload = dict(message["payload"])
        CreateQuoteUseCase(self._quote_repository, self._publisher).execute(
            CreateQuoteCommand(
                service_order_id=str(payload["service_order_id"]),
                items=list(self._default_items),
                amount=self._default_amount,
            )
        )
        self._processed_events.mark_processed(event_id, event_type, correlation_id)
        return "processed"
