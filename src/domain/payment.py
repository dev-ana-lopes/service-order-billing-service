from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from src.domain.events import DomainEvent


class QuoteStatus(StrEnum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    WAITING_PREFERENCE = "WAITING_PREFERENCE"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0"):
            raise ValueError("Money amount must be positive")
        if not self.currency.strip():
            raise ValueError("Currency is required")


@dataclass(frozen=True, slots=True)
class PaymentPreference:
    preference_id: str
    checkout_url: str


class PaymentGatewayPort(Protocol):
    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        pass


@dataclass(slots=True)
class Quote:
    service_order_id: str
    items: list[str]
    total: Money
    quote_id: str = field(default_factory=lambda: str(uuid4()))
    status: QuoteStatus = QuoteStatus.CREATED

    @classmethod
    def create(
        cls, service_order_id: str, items: list[str], total: Money
    ) -> tuple["Quote", DomainEvent]:
        if not service_order_id.strip():
            raise ValueError("Service order id is required")
        if not items:
            raise ValueError("At least one quote item is required")

        quote = cls(service_order_id=service_order_id, items=items, total=total)
        return quote, quote._event("QUOTE_CREATED", {"quote_id": quote.quote_id})

    def approve(self) -> DomainEvent:
        if self.status != QuoteStatus.CREATED:
            raise ValueError("Only created quotes can be approved")
        self.status = QuoteStatus.APPROVED
        return self._event("QUOTE_APPROVED", {"quote_id": self.quote_id})

    def cancel(self, reason: str) -> DomainEvent:
        if self.status == QuoteStatus.CANCELLED:
            raise ValueError("Quote is already cancelled")
        self.status = QuoteStatus.CANCELLED
        return self._event(
            "QUOTE_CANCELLED", {"quote_id": self.quote_id, "reason": reason}
        )

    def _event(self, event_type: str, payload: dict[str, str]) -> DomainEvent:
        base_payload = {"service_order_id": self.service_order_id}
        base_payload.update(payload)
        return DomainEvent(
            event_type=event_type,
            correlation_id=self.service_order_id,
            payload=base_payload,
        )


@dataclass(slots=True)
class Payment:
    quote_id: str
    service_order_id: str
    total: Money
    payment_id: str = field(default_factory=lambda: str(uuid4()))
    status: PaymentStatus = PaymentStatus.WAITING_PREFERENCE
    preference: PaymentPreference | None = None

    @classmethod
    def from_quote(cls, quote: Quote) -> "Payment":
        if quote.status != QuoteStatus.APPROVED:
            raise ValueError("Payment can only be created for approved quotes")
        return cls(
            quote_id=quote.quote_id,
            service_order_id=quote.service_order_id,
            total=quote.total,
        )

    def create_preference(self, gateway: PaymentGatewayPort) -> DomainEvent:
        if self.status != PaymentStatus.WAITING_PREFERENCE:
            raise ValueError("Payment preference was already requested")
        self.preference = gateway.create_checkout_preference(
            self.quote_id, self.service_order_id, self.total
        )
        self.status = PaymentStatus.PENDING
        return self._event(
            "PAYMENT_PREFERENCE_CREATED",
            {
                "payment_id": self.payment_id,
                "preference_id": self.preference.preference_id,
            },
        )

    def confirm(self) -> DomainEvent:
        if self.status != PaymentStatus.PENDING:
            raise ValueError("Only pending payments can be confirmed")
        self.status = PaymentStatus.CONFIRMED
        return self._event("PAYMENT_CONFIRMED", {"payment_id": self.payment_id})

    def fail(self, reason: str) -> DomainEvent:
        if self.status == PaymentStatus.CONFIRMED:
            raise ValueError("Confirmed payments cannot fail")
        self.status = PaymentStatus.FAILED
        return self._event(
            "PAYMENT_FAILED", {"payment_id": self.payment_id, "reason": reason}
        )

    def _event(self, event_type: str, payload: dict[str, str]) -> DomainEvent:
        base_payload = {
            "service_order_id": self.service_order_id,
            "quote_id": self.quote_id,
        }
        base_payload.update(payload)
        return DomainEvent(
            event_type=event_type,
            correlation_id=self.service_order_id,
            payload=base_payload,
        )
