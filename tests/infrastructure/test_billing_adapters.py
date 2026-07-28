from decimal import Decimal
from typing import Any

import pytest

from src.application.use_cases import (
    ApproveQuoteUseCase,
    CreateQuoteCommand,
    CreateQuoteUseCase,
)
from src.domain.events import DomainEvent
from src.domain.payment import (
    Money,
    Payment,
    PaymentGatewayError,
    PaymentPreference,
    PaymentStatus,
)
from src.infrastructure.messaging.in_memory_event_publisher import InMemoryEventPublisher
from src.infrastructure.payment.fake_payment_gateway import FakePaymentGateway
from src.infrastructure.payment.mercado_pago_checkout_adapter import (
    MercadoPagoCheckoutAdapter,
    MercadoPagoCheckoutSettings,
)
from src.infrastructure.payment.mercado_pago_sdk_client import MercadoPagoSdkClient
from src.infrastructure.repositories.in_memory_billing_repositories import (
    InMemoryPaymentRepository,
    InMemoryQuoteRepository,
)


class FakeMercadoPagoSdkClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def create_preference(
        self, payload: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        self.requests.append(
            {
                "operation": "create_preference",
                "payload": payload,
                "idempotency_key": idempotency_key,
            }
        )
        return self.response

    def search_payments(self, filters: dict[str, str]) -> dict[str, Any]:
        self.requests.append({"operation": "search_payments", "filters": filters})
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
    first = DomainEvent(event_type="QUOTE_CREATED", correlation_id="os-1", payload={})
    second = DomainEvent(event_type="QUOTE_APPROVED", correlation_id="os-1", payload={})

    publisher.publish(first)
    publisher.publish(second)

    assert publisher.events == [first, second]


def test_mercado_pago_adapter_creates_checkout_preference_payload() -> None:
    sdk_client = FakeMercadoPagoSdkClient(
        {"id": "pref-1", "sandbox_init_point": "https://sandbox.mercadopago.test/pref-1"}
    )
    adapter = MercadoPagoCheckoutAdapter(_settings(), sdk_client=sdk_client)

    preference = adapter.create_checkout_preference(
        quote_id="quote-1",
        service_order_id="os-1",
        total=Money(Decimal("120.00")),
    )

    request = sdk_client.requests[0]
    assert preference.preference_id == "pref-1"
    assert preference.checkout_url == "https://sandbox.mercadopago.test/pref-1"
    assert request["operation"] == "create_preference"
    assert request["idempotency_key"]
    assert request["payload"]["external_reference"] == "os-1"
    assert request["payload"]["items"][0]["currency_id"] == "BRL"
    assert request["payload"]["back_urls"]["success"] == "https://app.test/success"
    assert "notification_url" not in request["payload"]


def test_mercado_pago_adapter_requires_access_token_and_checkout_url() -> None:
    with pytest.raises(ValueError, match="access token is required"):
        MercadoPagoCheckoutAdapter(_settings(access_token=""))

    adapter = MercadoPagoCheckoutAdapter(
        _settings(), sdk_client=FakeMercadoPagoSdkClient({"id": "pref-1"})
    )
    with pytest.raises(ValueError, match="checkout URL"):
        adapter.create_checkout_preference("quote-1", "os-1", Money(Decimal("120.00")))


def test_mercado_pago_adapter_reads_one_matching_payment() -> None:
    sdk_client = FakeMercadoPagoSdkClient(
        {
            "results": [
                {
                    "id": "mp-payment-1",
                    "external_reference": "os-1",
                    "status": "approved",
                    "status_detail": "accredited",
                    "transaction_amount": 120.0,
                    "currency_id": "BRL",
                }
            ]
        }
    )
    adapter = MercadoPagoCheckoutAdapter(_settings(), sdk_client=sdk_client)
    payment = Payment(
        quote_id="quote-1",
        service_order_id="os-1",
        total=Money(Decimal("120.00")),
        preference=PaymentPreference(
            preference_id="pref-1",
            checkout_url="https://checkout.test/pref-1",
            external_reference="os-1",
        ),
        status=PaymentStatus.PENDING,
    )

    result = adapter.get_payment_status(payment)

    assert result.provider_payment_id == "mp-payment-1"
    assert result.status == "approved"
    assert result.status_detail == "accredited"
    assert sdk_client.requests[0]["operation"] == "search_payments"
    assert sdk_client.requests[0]["filters"]["external_reference"] == "os-1"


def test_mercado_pago_adapter_rejects_ambiguous_payment_search() -> None:
    sdk_client = FakeMercadoPagoSdkClient(
        {
            "results": [
                {
                    "id": "mp-payment-1",
                    "external_reference": "os-1",
                    "status": "pending",
                    "transaction_amount": 120.0,
                    "currency_id": "BRL",
                },
                {
                    "id": "mp-payment-2",
                    "external_reference": "os-1",
                    "status": "approved",
                    "transaction_amount": 120.0,
                    "currency_id": "BRL",
                },
            ]
        }
    )
    adapter = MercadoPagoCheckoutAdapter(_settings(), sdk_client=sdk_client)
    payment = Payment(
        quote_id="quote-1",
        service_order_id="os-1",
        total=Money(Decimal("120.00")),
        preference=PaymentPreference("pref-1", "https://checkout.test/pref-1", "os-1"),
        status=PaymentStatus.PENDING,
    )

    with pytest.raises(PaymentGatewayError, match="More than one"):
        adapter.get_payment_status(payment)


def test_sdk_client_translates_provider_error(monkeypatch) -> None:
    class FailingPreference:
        def create(self, payload, options):
            del payload, options
            raise RuntimeError("provider rejected request")

    class FailingSdk:
        def preference(self):
            return FailingPreference()

    monkeypatch.setattr(
        "src.infrastructure.payment.mercado_pago_sdk_client.mercadopago.SDK",
        lambda access_token: FailingSdk(),
    )
    client = MercadoPagoSdkClient("test-token")

    with pytest.raises(PaymentGatewayError, match="status 502"):
        client.create_preference({}, "idempotency-key")


def test_sdk_client_sanitizes_authorization_errors(monkeypatch) -> None:
    class UnauthorizedError(Exception):
        status_code = 403

    class FailingPreference:
        def create(self, payload, options):
            del payload, options
            raise UnauthorizedError("token=secret-token")

    class FailingSdk:
        def preference(self):
            return FailingPreference()

    monkeypatch.setattr(
        "src.infrastructure.payment.mercado_pago_sdk_client.mercadopago.SDK",
        lambda access_token: FailingSdk(),
    )
    client = MercadoPagoSdkClient("secret-token")

    with pytest.raises(PaymentGatewayError) as error:
        client.create_preference({}, "idempotency-key")

    assert error.value.status_code == 403
    assert "secret-token" not in str(error.value)
    assert "MERCADO_PAGO_ACCESS_TOKEN" in str(error.value)


def _settings(access_token: str = "test-token") -> MercadoPagoCheckoutSettings:
    return MercadoPagoCheckoutSettings(
        access_token=access_token,
        success_url="https://app.test/success",
        failure_url="https://app.test/failure",
        pending_url="https://app.test/pending",
    )
