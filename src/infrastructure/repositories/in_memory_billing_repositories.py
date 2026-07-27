from __future__ import annotations

from src.domain.payment import Payment, Quote


class InMemoryQuoteRepository:
    def __init__(self) -> None:
        self._items: dict[str, Quote] = {}

    def save(self, quote: Quote) -> None:
        self._items[quote.quote_id] = quote

    def get(self, quote_id: str) -> Quote:
        try:
            return self._items[quote_id]
        except KeyError as exc:
            raise KeyError(f"Quote not found: {quote_id}") from exc

    def get_by_service_order_id(self, service_order_id: str) -> Quote:
        for quote in self._items.values():
            if quote.service_order_id == service_order_id:
                return quote
        raise KeyError(f"Quote not found for service order: {service_order_id}")


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self._items: dict[str, Payment] = {}

    def save(self, payment: Payment) -> None:
        self._items[payment.payment_id] = payment

    def get(self, payment_id: str) -> Payment:
        try:
            return self._items[payment_id]
        except KeyError as exc:
            raise KeyError(f"Payment not found: {payment_id}") from exc

    def get_by_service_order_id(self, service_order_id: str) -> Payment:
        for payment in self._items.values():
            if payment.service_order_id == service_order_id:
                return payment
        raise KeyError(f"Payment not found for service order: {service_order_id}")
