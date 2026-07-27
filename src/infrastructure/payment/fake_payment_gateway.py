from __future__ import annotations

from src.domain.payment import (
    Money,
    Payment,
    PaymentGatewayError,
    PaymentPreference,
    PaymentProviderStatus,
)


class FakePaymentGateway:
    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        return PaymentPreference(
            preference_id=f"fake-{quote_id}",
            checkout_url=f"https://checkout.local/{service_order_id}",
            external_reference=service_order_id,
        )

    def get_payment_status(self, payment: Payment) -> PaymentProviderStatus:
        raise PaymentGatewayError(
            "Payment status synchronization is available only in Mercado Pago mode.",
            status_code=501,
        )
