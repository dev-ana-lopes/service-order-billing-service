from decimal import Decimal
from typing import Any

import pytest

from src.application.use_cases import (
    ApproveQuoteUseCase,
    CreateQuoteCommand,
    CreateQuoteUseCase,
)
from src.domain.events import DomainEvent
from src.domain.payment import Money, PaymentStatus
from src.infrastructure.messaging.in_memory_event_publisher import InMemoryEventPublisher
from src.infrastructure.payment.fake_payment_gateway import FakePaymentGateway
from src.infrastructure.payment.mercado_pago_checkout_adapter import (
    MercadoPagoCheckoutAdapter,
    MercadoPagoCheckoutSettings,
)
from src.infrastructure.repositories.in_memory_billing_repositories import (
    InMemoryPaymentRepository,
    InMemoryQuoteRepository,
)


class FakeHttpJsonClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        self.requests.append({"url": url, "headers": headers, "payload": payload})
        return self.response


def test_in_memory_adapters_support_quote_approval_flow() -> None:
    quote_repository = InMemoryQuoteRepository()
    payment_repository = InMemoryPaymentRepository()
    publisher = InMemoryEventPublisher()
    quote = CreateQuoteUseCase(quote_repository, publisher).execute(
        CreateQuoteCommand("os-1", ["Brake pads"], Decimal("120.00"))
    )

    payment = ApproveQuoteUseCase(
        quote_repository,
        payment_repository,
        publisher,
        FakePaymentGateway(),
    ).execute(quote.quote_id)

    assert quote_repository.get_by_service_order_id("os-1") is quote
    assert payment_repository.get(payment.payment_id).status == PaymentStatus.PENDING
    assert [event.event_type for event in publisher.events] == [
        "QUOTE_CREATED",
        "QUOTE_APPROVED",
        "PAYMENT_PREFERENCE_CREATED",
    ]


def test_in_memory_repositories_raise_clear_errors_when_missing() -> None:
    with pytest.raises(KeyError, match="Quote not found"):
        InMemoryQuoteRepository().get("missing")
    with pytest.raises(KeyError, match="Payment not found"):
        InMemoryPaymentRepository().get("missing")


def test_in_memory_publisher_keeps_event_order() -> None:
    publisher = InMemoryEventPublisher()
    first = DomainEvent(event_type="FIRST", correlation_id="os-1", payload={})
    second = DomainEvent(event_type="SECOND", correlation_id="os-1", payload={})

    publisher.publish(first)
    publisher.publish(second)

    assert publisher.events == [first, second]


def test_mercado_pago_adapter_creates_checkout_preference_payload() -> None:
    http_client = FakeHttpJsonClient(
        {"id": "pref-1", "sandbox_init_point": "https://sandbox.mercadopago.test/pref-1"}
    )
    adapter = MercadoPagoCheckoutAdapter(_settings(), http_client=http_client)

    preference = adapter.create_checkout_preference(
        quote_id="quote-1",
        service_order_id="os-1",
        total=Money(Decimal("120.00")),
    )

    request = http_client.requests[0]
    assert preference.preference_id == "pref-1"
    assert preference.checkout_url == "https://sandbox.mercadopago.test/pref-1"
    assert request["url"] == "https://api.mercadopago.com/checkout/preferences"
    assert request["headers"]["Authorization"] == "Bearer test-token"
    assert request["payload"]["external_reference"] == "os-1"
    assert request["payload"]["items"][0]["currency_id"] == "BRL"
    assert request["payload"]["back_urls"]["success"] == "https://app.test/success"


def test_mercado_pago_adapter_requires_access_token_and_checkout_url() -> None:
    with pytest.raises(ValueError, match="access token is required"):
        MercadoPagoCheckoutAdapter(_settings(access_token=""))

    adapter = MercadoPagoCheckoutAdapter(
        _settings(), http_client=FakeHttpJsonClient({"id": "pref-1"})
    )
    with pytest.raises(ValueError, match="checkout URL"):
        adapter.create_checkout_preference("quote-1", "os-1", Money(Decimal("120.00")))


def _settings(access_token: str = "test-token") -> MercadoPagoCheckoutSettings:
    return MercadoPagoCheckoutSettings(
        access_token=access_token,
        api_base_url="https://api.mercadopago.com",
        success_url="https://app.test/success",
        failure_url="https://app.test/failure",
        pending_url="https://app.test/pending",
    )
