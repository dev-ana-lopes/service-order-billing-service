from __future__ import annotations

from src.domain.payment import Money, PaymentPreference


class FakePaymentGateway:
    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        return PaymentPreference(
            preference_id=f"fake-{quote_id}",
            checkout_url=f"https://checkout.local/{service_order_id}",
        )
