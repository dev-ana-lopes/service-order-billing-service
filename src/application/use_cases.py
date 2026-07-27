from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from src.application.ports import (
    EventPublisherPort,
    PaymentGatewayPort,
    PaymentRepositoryPort,
    QuoteRepositoryPort,
)
from src.domain.payment import Money, Payment, PaymentStatus, Quote


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


@dataclass(frozen=True, slots=True)
class ApplyPaymentStatusCommand:
    payment_id: str
    provider_status: str
    provider_status_detail: str | None = None


@dataclass(frozen=True, slots=True)
class ApplyPaymentStatusResult:
    payment: Payment
    action: Literal["confirmed", "failed", "ignored", "duplicate"]
    published_event_type: str | None = None


class ApplyPaymentStatusUseCase:
    def __init__(
        self, repository: PaymentRepositoryPort, publisher: EventPublisherPort
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    def execute(self, command: ApplyPaymentStatusCommand) -> ApplyPaymentStatusResult:
        payment = self._repository.get(command.payment_id)
        normalized_status = command.provider_status.strip().lower()
        event = None
        action: Literal["confirmed", "failed", "ignored", "duplicate"]

        if normalized_status in {"approved", "accredited"}:
            if payment.status == PaymentStatus.CONFIRMED:
                action = "duplicate"
            elif payment.status == PaymentStatus.FAILED:
                action = "ignored"
            else:
                event = payment.confirm()
                action = "confirmed"
        elif normalized_status in {
            "rejected",
            "cancelled",
            "refunded",
            "charged_back",
            "expired",
            "failure",
        }:
            if payment.status == PaymentStatus.CONFIRMED:
                action = "ignored"
            elif payment.status == PaymentStatus.FAILED:
                action = "duplicate"
            else:
                event = payment.fail(
                    command.provider_status_detail
                    or f"Mercado Pago status: {command.provider_status}"
                )
                action = "failed"
        elif normalized_status in {"pending", "in_process"}:
            action = "ignored"
        else:
            raise ValueError(
                f"Unsupported Mercado Pago status: {command.provider_status}"
            )

        self._repository.save(payment)
        if event is not None:
            self._publisher.publish(event)
        return ApplyPaymentStatusResult(
            payment=payment,
            action=action,
            published_event_type=None if event is None else event.event_type,
        )


@dataclass(frozen=True, slots=True)
class SyncPaymentStatusResult:
    payment: Payment
    provider_payment_id: str
    provider_status: str
    provider_status_detail: str | None
    action: Literal["confirmed", "failed", "ignored", "duplicate"]
    published_event_type: str | None


class SyncPaymentStatusUseCase:
    def __init__(
        self,
        payment_repository: PaymentRepositoryPort,
        publisher: EventPublisherPort,
        payment_gateway: PaymentGatewayPort,
    ) -> None:
        self._payment_repository = payment_repository
        self._publisher = publisher
        self._payment_gateway = payment_gateway

    def execute(self, payment_id: str) -> SyncPaymentStatusResult:
        payment = self._payment_repository.get(payment_id)
        provider_status = self._payment_gateway.get_payment_status(payment)
        result = ApplyPaymentStatusUseCase(
            self._payment_repository, self._publisher
        ).execute(
            ApplyPaymentStatusCommand(
                payment_id=payment_id,
                provider_status=provider_status.status,
                provider_status_detail=provider_status.status_detail,
            )
        )
        return SyncPaymentStatusResult(
            payment=result.payment,
            provider_payment_id=provider_status.provider_payment_id,
            provider_status=provider_status.status,
            provider_status_detail=provider_status.status_detail,
            action=result.action,
            published_event_type=result.published_event_type,
        )
