from decimal import Decimal

from src.application.use_cases import (
    ApproveQuoteUseCase,
    ConfirmPaymentUseCase,
    CreateQuoteCommand,
    CreateQuoteUseCase,
    FailPaymentUseCase,
)
from src.domain.events import DomainEvent
from src.domain.payment import (
    Money,
    Payment,
    PaymentPreference,
    PaymentStatus,
    Quote,
    QuoteStatus,
)


class InMemoryQuoteRepository:
    def __init__(self) -> None:
        self.items: dict[str, Quote] = {}

    def save(self, quote: Quote) -> None:
        self.items[quote.quote_id] = quote

    def get(self, quote_id: str) -> Quote:
        return self.items[quote_id]

    def get_by_service_order_id(self, service_order_id: str) -> Quote:
        return next(
            quote
            for quote in self.items.values()
            if quote.service_order_id == service_order_id
        )


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self.items: dict[str, Payment] = {}

    def save(self, payment: Payment) -> None:
        self.items[payment.payment_id] = payment

    def get(self, payment_id: str) -> Payment:
        return self.items[payment_id]


class EventCollector:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


class FakePaymentGateway:
    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ) -> PaymentPreference:
        return PaymentPreference(
            preference_id=f"pref-{quote_id}",
            checkout_url=f"https://checkout.test/{service_order_id}",
        )


def test_create_quote_persists_and_publishes_event() -> None:
    quote_repository = InMemoryQuoteRepository()
    publisher = EventCollector()

    quote = CreateQuoteUseCase(quote_repository, publisher).execute(
        CreateQuoteCommand("os-1", ["Brake pads"], Decimal("120.00"))
    )

    assert quote_repository.get(quote.quote_id).status == QuoteStatus.CREATED
    assert publisher.events[0].event_type == "QUOTE_CREATED"


def test_approve_quote_creates_payment_preference() -> None:
    quote_repository = InMemoryQuoteRepository()
    payment_repository = InMemoryPaymentRepository()
    publisher = EventCollector()
    quote = CreateQuoteUseCase(quote_repository, publisher).execute(
        CreateQuoteCommand("os-1", ["Brake pads"], Decimal("120.00"))
    )

    payment = ApproveQuoteUseCase(
        quote_repository,
        payment_repository,
        publisher,
        FakePaymentGateway(),
    ).execute(quote.quote_id)

    assert quote.status == QuoteStatus.APPROVED
    assert payment.status == PaymentStatus.PENDING
    assert payment.preference is not None
    assert [event.event_type for event in publisher.events] == [
        "QUOTE_CREATED",
        "QUOTE_APPROVED",
        "PAYMENT_PREFERENCE_CREATED",
    ]


def test_confirm_and_fail_payment_publish_terminal_events() -> None:
    quote_repository = InMemoryQuoteRepository()
    payment_repository = InMemoryPaymentRepository()
    publisher = EventCollector()
    quote = CreateQuoteUseCase(quote_repository, publisher).execute(
        CreateQuoteCommand("os-1", ["Brake pads"], Decimal("120.00"))
    )
    payment = ApproveQuoteUseCase(
        quote_repository,
        payment_repository,
        publisher,
        FakePaymentGateway(),
    ).execute(quote.quote_id)

    confirmed = ConfirmPaymentUseCase(payment_repository, publisher).execute(
        payment.payment_id
    )

    assert confirmed.status == PaymentStatus.CONFIRMED
    assert publisher.events[-1].event_type == "PAYMENT_CONFIRMED"

    failed_quote = CreateQuoteUseCase(quote_repository, publisher).execute(
        CreateQuoteCommand("os-2", ["Oil change"], Decimal("90.00"))
    )
    failed_payment = ApproveQuoteUseCase(
        quote_repository,
        payment_repository,
        publisher,
        FakePaymentGateway(),
    ).execute(failed_quote.quote_id)

    failed = FailPaymentUseCase(payment_repository, publisher).execute(
        failed_payment.payment_id, "Card rejected"
    )

    assert failed.status == PaymentStatus.FAILED
    assert publisher.events[-1].event_type == "PAYMENT_FAILED"
