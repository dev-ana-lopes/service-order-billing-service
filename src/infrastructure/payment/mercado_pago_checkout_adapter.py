from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import request

from src.domain.payment import Money, PaymentPreference


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
        with request.urlopen(http_request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))


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
