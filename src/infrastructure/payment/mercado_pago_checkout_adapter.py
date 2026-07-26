from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import request
from urllib.error import HTTPError, URLError

from src.domain.payment import Money, PaymentGatewayError, PaymentPreference


class HttpJsonClientPort(Protocol):
    def post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        pass


class UrllibHttpJsonClient:
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
            with request.urlopen(http_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace").strip()
            detail = f"Mercado Pago request failed with status {exc.code}"
            if exc.code in {401, 403}:
                detail = (
                    f"{detail}. Check whether MERCADO_PAGO_ACCESS_TOKEN is valid "
                    "for the configured Mercado Pago environment."
                )
            if response_body:
                detail = f"{detail} Response: {response_body[:300]}"
            raise PaymentGatewayError(
                detail,
                status_code=exc.code,
                response_body=response_body,
            ) from exc
        except URLError as exc:
            raise PaymentGatewayError(
                "Mercado Pago request could not reach the payment gateway."
            ) from exc


@dataclass(frozen=True, slots=True)
class MercadoPagoCheckoutSettings:
    access_token: str
    api_base_url: str
    success_url: str
    failure_url: str
    pending_url: str


class MercadoPagoCheckoutAdapter:
    def __init__(
        self,
        settings: MercadoPagoCheckoutSettings,
        http_client: HttpJsonClientPort | None = None,
    ) -> None:
        if not settings.access_token.strip():
            raise ValueError("Mercado Pago access token is required")
        self._settings = settings
        self._http_client = http_client or UrllibHttpJsonClient()

    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        response = self._http_client.post_json(
            url=f"{self._settings.api_base_url.rstrip('/')}/checkout/preferences",
            headers={
                "Authorization": f"Bearer {self._settings.access_token}",
                "Content-Type": "application/json",
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
        return PaymentPreference(preference_id=preference_id, checkout_url=checkout_url)
