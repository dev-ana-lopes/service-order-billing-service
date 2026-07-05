from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.application.ports import (
    EventPublisherPort,
    PaymentGatewayPort,
    PaymentRepositoryPort,
    QuoteRepositoryPort,
)
from src.domain.payment import Money, Payment, Quote


@dataclass(frozen=True, slots=True)
class CreateQuoteCommand:
    service_order_id: str
    items: list[str]
    amount: Decimal


class CreateQuoteUseCase:
    def __init__(
        self, repository: QuoteRepositoryPort, publisher: EventPublisherPort
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    def execute(self, command: CreateQuoteCommand) -> Quote:
        quote, event = Quote.create(
            service_order_id=command.service_order_id,
            items=command.items,
            total=Money(command.amount),
        )
        self._repository.save(quote)
        self._publisher.publish(event)
        return quote


class ApproveQuoteUseCase:
    def __init__(
        self,
        quote_repository: QuoteRepositoryPort,
        payment_repository: PaymentRepositoryPort,
        publisher: EventPublisherPort,
        payment_gateway: PaymentGatewayPort,
    ) -> None:
        self._quote_repository = quote_repository
        self._payment_repository = payment_repository
        self._publisher = publisher
        self._payment_gateway = payment_gateway

    def execute(self, quote_id: str) -> Payment:
        quote = self._quote_repository.get(quote_id)
        approved_event = quote.approve()
        payment = Payment.from_quote(quote)
        preference_event = payment.create_preference(self._payment_gateway)

        self._quote_repository.save(quote)
        self._payment_repository.save(payment)
        self._publisher.publish(approved_event)
        self._publisher.publish(preference_event)
        return payment


class ConfirmPaymentUseCase:
    def __init__(
        self, repository: PaymentRepositoryPort, publisher: EventPublisherPort
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    def execute(self, payment_id: str) -> Payment:
        payment = self._repository.get(payment_id)
        event = payment.confirm()
        self._repository.save(payment)
        self._publisher.publish(event)
        return payment


class FailPaymentUseCase:
    def __init__(
        self, repository: PaymentRepositoryPort, publisher: EventPublisherPort
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    def execute(self, payment_id: str, reason: str) -> Payment:
        payment = self._repository.get(payment_id)
        event = payment.fail(reason)
        self._repository.save(payment)
        self._publisher.publish(event)
        return payment
