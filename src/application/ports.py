from __future__ import annotations

from typing import Protocol

from src.domain.events import DomainEvent
from src.domain.payment import Payment, PaymentGatewayPort, Quote


class QuoteRepositoryPort(Protocol):
    def save(self, quote: Quote) -> None:
        ...

    def get(self, quote_id: str) -> Quote:
        ...

    def get_by_service_order_id(self, service_order_id: str) -> Quote:
        ...


class PaymentRepositoryPort(Protocol):
    def save(self, payment: Payment) -> None:
        ...

    def get(self, payment_id: str) -> Payment:
        ...


class EventPublisherPort(Protocol):
    def publish(self, event: DomainEvent) -> None:
        ...


class ProcessedEventRepositoryPort(Protocol):
    def is_processed(self, event_id: str) -> bool:
        ...

    def mark_processed(
        self, event_id: str, event_type: str, correlation_id: str
    ) -> None:
        ...


__all__ = [
    "EventPublisherPort",
    "PaymentGatewayPort",
    "PaymentRepositoryPort",
    "QuoteRepositoryPort",
]
