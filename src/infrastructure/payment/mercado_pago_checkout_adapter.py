from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.domain.payment import (
    Money,
    Payment,
    PaymentGatewayError,
    PaymentPreference,
    PaymentProviderStatus,
)
from src.infrastructure.payment.mercado_pago_sdk_client import (
    MercadoPagoSdkClient,
    MercadoPagoSdkClientPort,
    new_idempotency_key,
)


@dataclass(frozen=True, slots=True)
class MercadoPagoCheckoutSettings:
    access_token: str
    success_url: str
    failure_url: str
    pending_url: str
    timeout_seconds: int = 10


class MercadoPagoCheckoutAdapter:
    def __init__(
        self,
        settings: MercadoPagoCheckoutSettings,
        sdk_client: MercadoPagoSdkClientPort | None = None,
    ) -> None:
        if not settings.access_token.strip():
            raise ValueError("Mercado Pago access token is required")
        self._settings = settings
        self._sdk_client = sdk_client or MercadoPagoSdkClient(
            settings.access_token,
            timeout_seconds=settings.timeout_seconds,
        )

    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        response = self._sdk_client.create_preference(
            payload={
                "external_reference": service_order_id,
                "items": [
                    {
                        "id": quote_id,
                        "title": f"Service order {service_order_id}",
                        "quantity": 1,
                        "currency_id": total.currency,
                        "unit_price": float(total.amount),
                    }
                ],
                "back_urls": {
                    "success": self._settings.success_url,
                    "failure": self._settings.failure_url,
                    "pending": self._settings.pending_url,
                },
            },
            idempotency_key=new_idempotency_key(),
        )
        preference_id = str(response.get("id", "")).strip()
        checkout_url = response.get("init_point") or response.get("sandbox_init_point")
        if not preference_id:
            raise ValueError("Mercado Pago preference response did not include an id")
        if not checkout_url:
            raise ValueError(
                "Mercado Pago preference response did not include checkout URL"
            )
        return PaymentPreference(
            preference_id=preference_id,
            checkout_url=str(checkout_url),
            external_reference=service_order_id,
        )

    def get_payment_status(self, payment: Payment) -> PaymentProviderStatus:
        if payment.preference is None or not payment.preference.external_reference:
            raise PaymentGatewayError(
                "Payment has no Mercado Pago external reference.", status_code=422
            )

        response = self._sdk_client.search_payments(
            {
                "external_reference": payment.preference.external_reference,
                "sort": "date_created",
                "criteria": "desc",
            }
        )
        results = response.get("results")
        if not isinstance(results, list):
            raise PaymentGatewayError(
                "Mercado Pago payment search returned an invalid response.",
                status_code=502,
            )
        matches = [
            item
            for item in results
            if isinstance(item, dict)
            and str(item.get("external_reference", ""))
            == payment.preference.external_reference
        ]
        if not matches:
            raise PaymentGatewayError(
                "No Mercado Pago payment was found for this payment.", status_code=404
            )
        if len(matches) > 1:
            raise PaymentGatewayError(
                "More than one Mercado Pago payment matches this external reference.",
                status_code=409,
            )

        provider_payment = matches[0]
        provider_amount = provider_payment.get("transaction_amount")
        provider_currency = str(provider_payment.get("currency_id", ""))
        if (
            provider_amount is None
            or Decimal(str(provider_amount)) != payment.total.amount
        ):
            raise PaymentGatewayError(
                "Mercado Pago payment amount does not match the billing amount.",
                status_code=409,
            )
        if provider_currency != payment.total.currency:
            raise PaymentGatewayError(
                "Mercado Pago payment currency does not match the billing currency.",
                status_code=409,
            )

        provider_payment_id = str(provider_payment.get("id", "")).strip()
        provider_status = str(provider_payment.get("status", "")).strip()
        if not provider_payment_id or not provider_status:
            raise PaymentGatewayError(
                "Mercado Pago payment response is missing id or status.",
                status_code=502,
            )
        return PaymentProviderStatus(
            provider_payment_id=provider_payment_id,
            status=provider_status,
            status_detail=(
                str(provider_payment["status_detail"])
                if provider_payment.get("status_detail") is not None
                else None
            ),
        )
