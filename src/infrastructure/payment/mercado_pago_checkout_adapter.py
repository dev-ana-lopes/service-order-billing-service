from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from uuid import uuid4

from src.domain.payment import (
    Money,
    Payment,
    PaymentGatewayError,
    PaymentPreference,
    PaymentProviderStatus,
)


class HttpJsonClientPort(Protocol):
    def post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        pass

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        pass


class UrllibHttpJsonClient:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self._timeout_seconds = timeout_seconds

    def post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(
                http_request, timeout=self._timeout_seconds
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise _build_payment_gateway_error(exc) from exc
        except URLError as exc:
            raise PaymentGatewayError(
                "Mercado Pago request could not reach the payment gateway."
            ) from exc

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        http_request = request.Request(url=url, headers=headers, method="GET")
        try:
            with request.urlopen(
                http_request, timeout=self._timeout_seconds
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise _build_payment_gateway_error(exc) from exc
        except URLError as exc:
            raise PaymentGatewayError(
                "Mercado Pago request could not reach the payment gateway."
            ) from exc


def _build_payment_gateway_error(exc: HTTPError) -> PaymentGatewayError:
    response_body = exc.read().decode("utf-8", errors="replace").strip()
    detail = f"Mercado Pago request failed with status {exc.code}"
    if exc.code in {401, 403}:
        detail = (
            f"{detail}. Check whether MERCADO_PAGO_ACCESS_TOKEN is valid "
            "for the configured Mercado Pago environment."
        )
    if response_body:
        detail = f"{detail} Response: {response_body[:300]}"
    return PaymentGatewayError(
        detail,
        status_code=exc.code,
        response_body=response_body,
    )


@dataclass(frozen=True, slots=True)
class MercadoPagoCheckoutSettings:
    access_token: str
    api_base_url: str
    success_url: str
    failure_url: str
    pending_url: str
    timeout_seconds: int = 10


class MercadoPagoCheckoutAdapter:
    def __init__(
        self,
        settings: MercadoPagoCheckoutSettings,
        http_client: HttpJsonClientPort | None = None,
    ) -> None:
        if not settings.access_token.strip():
            raise ValueError("Mercado Pago access token is required")
        self._settings = settings
        self._http_client = http_client or UrllibHttpJsonClient(
            timeout_seconds=settings.timeout_seconds
        )

    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        response = self._http_client.post_json(
            url=f"{self._settings.api_base_url.rstrip('/')}/checkout/preferences",
            headers={
                "Authorization": f"Bearer {self._settings.access_token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": str(uuid4()),
            },
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
        )
        preference_id = str(response["id"])
        checkout_url = response.get("init_point") or response.get("sandbox_init_point")
        if not checkout_url:
            raise ValueError(
                "Mercado Pago preference response did not include checkout URL"
            )
        return PaymentPreference(
            preference_id=preference_id,
            checkout_url=checkout_url,
            external_reference=service_order_id,
        )

    def get_payment_status(self, payment: Payment) -> PaymentProviderStatus:
        if payment.preference is None or not payment.preference.external_reference:
            raise PaymentGatewayError(
                "Payment has no Mercado Pago external reference.", status_code=422
            )

        query = urlencode(
            {
                "external_reference": payment.preference.external_reference,
                "sort": "date_created",
                "criteria": "desc",
            }
        )
        response = self._http_client.get_json(
            url=f"{self._settings.api_base_url.rstrip('/')}/v1/payments/search?{query}",
            headers={
                "Authorization": f"Bearer {self._settings.access_token}",
                "Content-Type": "application/json",
            },
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
