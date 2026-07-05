from __future__ import annotations

from typing import Protocol

from src.domain.events import DomainEvent
from src.domain.payment import Payment, PaymentGatewayPort, Quote


class QuoteRepositoryPort(Protocol):
    def save(self, quote: Quote) -> None:
        pass

    def get(self, quote_id: str) -> Quote:
        pass

    def get_by_service_order_id(self, service_order_id: str) -> Quote:
        pass


class PaymentRepositoryPort(Protocol):
    def save(self, payment: Payment) -> None:
        pass

    def get(self, payment_id: str) -> Payment:
        pass


class EventPublisherPort(Protocol):
    def publish(self, event: DomainEvent) -> None:
        pass


__all__ = [
    "EventPublisherPort",
    "PaymentGatewayPort",
    "PaymentRepositoryPort",
    "QuoteRepositoryPort",
]
