from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

import mercadopago
from mercadopago.config import RequestOptions

from src.domain.payment import PaymentGatewayError


class MercadoPagoSdkClientPort(Protocol):
    def create_preference(
        self, payload: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        pass

    def search_payments(self, filters: dict[str, str]) -> dict[str, Any]:
        pass


class MercadoPagoSdkClient:
    def __init__(self, access_token: str, timeout_seconds: int = 10) -> None:
        if not access_token.strip():
            raise ValueError("Mercado Pago access token is required")

        self._sdk = mercadopago.SDK(access_token)
        self._timeout_seconds = float(timeout_seconds)

    def create_preference(
        self, payload: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        options = self._request_options(idempotency_key)
        return self._execute(lambda: self._sdk.preference().create(payload, options))

    def search_payments(self, filters: dict[str, str]) -> dict[str, Any]:
        return self._execute(lambda: self._sdk.payment().search(filters))

    def _request_options(self, idempotency_key: str) -> RequestOptions:
        return RequestOptions(
            connection_timeout=self._timeout_seconds,
            custom_headers={"x-idempotency-key": idempotency_key},
        )

    @staticmethod
    def _execute(call):
        try:
            result = call()
        except Exception as exc:  # SDK exceptions vary between releases.
            raise MercadoPagoSdkClient._translate_error(exc) from exc

        if not isinstance(result, dict):
            raise PaymentGatewayError(
                "Mercado Pago SDK returned an invalid response.", status_code=502
            )

        status_code = result.get("status")
        response = result.get("response")
        if isinstance(status_code, int) and status_code >= 400:
            raise PaymentGatewayError(
                MercadoPagoSdkClient._status_message(status_code),
                status_code=status_code,
            )
        if not isinstance(response, dict):
            raise PaymentGatewayError(
                "Mercado Pago SDK returned an invalid response.", status_code=502
            )
        return response

    @staticmethod
    def _translate_error(exc: Exception) -> PaymentGatewayError:
        status_code = getattr(exc, "status_code", None)
        if not isinstance(status_code, int):
            status_code = getattr(exc, "status", None)
        if not isinstance(status_code, int):
            status_code = 502
        return PaymentGatewayError(
            MercadoPagoSdkClient._status_message(status_code),
            status_code=status_code,
        )

    @staticmethod
    def _status_message(status_code: int) -> str:
        if status_code in {401, 403}:
            return (
                "Mercado Pago request was rejected. Check whether "
                "MERCADO_PAGO_ACCESS_TOKEN is valid for the configured environment."
            )
        return f"Mercado Pago request failed with status {status_code}."


def new_idempotency_key() -> str:
    return str(uuid4())
