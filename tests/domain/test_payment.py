from decimal import Decimal

import pytest

from src.domain.payment import (
    Money,
    Payment,
    PaymentPreference,
    PaymentStatus,
    Quote,
    QuoteStatus,
)


class FakePaymentGateway:
    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        assert quote_id
        assert service_order_id
        assert total.amount == Decimal("120.00")
        return PaymentPreference(
            preference_id="pref-1", checkout_url="https://checkout.test/pref-1"
        )


def test_create_quote_emits_quote_created_event() -> None:
    quote, event = Quote.create("os-1", ["Brake pads"], Money(Decimal("120.00")))

    assert quote.status == QuoteStatus.CREATED
    assert event.event_type == "QUOTE_CREATED"
    assert event.payload["service_order_id"] == "os-1"


def test_approve_quote_allows_payment_preference_creation() -> None:
    quote, _ = Quote.create("os-1", ["Brake pads"], Money(Decimal("120.00")))
    approved_event = quote.approve()
    payment = Payment.from_quote(quote)

    preference_event = payment.create_preference(FakePaymentGateway())

    assert approved_event.event_type == "QUOTE_APPROVED"
    assert payment.status == PaymentStatus.PENDING
    assert payment.preference is not None
    assert preference_event.event_type == "PAYMENT_PREFERENCE_CREATED"


def test_payment_confirmation_requires_pending_status() -> None:
    quote, _ = Quote.create("os-1", ["Brake pads"], Money(Decimal("120.00")))
    quote.approve()
    payment = Payment.from_quote(quote)

    with pytest.raises(ValueError, match="Only pending payments can be confirmed"):
        payment.confirm()


def test_failed_payment_emits_compensation_event() -> None:
    quote, _ = Quote.create("os-1", ["Brake pads"], Money(Decimal("120.00")))
    quote.approve()
    payment = Payment.from_quote(quote)

    event = payment.fail("Card rejected")

    assert payment.status == PaymentStatus.FAILED
    assert event.event_type == "PAYMENT_FAILED"
    assert event.payload["reason"] == "Card rejected"
