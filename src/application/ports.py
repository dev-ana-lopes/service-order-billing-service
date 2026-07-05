"""Application ports for billing persistence, messaging, and payment gateway."""

from __future__ import annotations

from typing import Protocol

from src.domain.events import DomainEvent
from src.domain.payment import Payment, PaymentGatewayPort, Quote


class QuoteRepositoryPort(Protocol):
    def save(self, quote: Quote) -> None:
        """Persist quote state."""

    def get(self, quote_id: str) -> Quote:
        """Return a quote by id."""

    def get_by_service_order_id(self, service_order_id: str) -> Quote:
        """Return the quote related to a service order."""


class PaymentRepositoryPort(Protocol):
    def save(self, payment: Payment) -> None:
        """Persist payment state."""

    def get(self, payment_id: str) -> Payment:
        """Return a payment by id."""


class EventPublisherPort(Protocol):
    def publish(self, event: DomainEvent) -> None:
        """Publish an integration event."""


__all__ = [
    "EventPublisherPort",
    "PaymentGatewayPort",
    "PaymentRepositoryPort",
    "QuoteRepositoryPort",
]
