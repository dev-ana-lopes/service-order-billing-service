from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from src.application.use_cases import (
    ApproveQuoteUseCase,
    ConfirmPaymentUseCase,
    CreateQuoteCommand,
    CreateQuoteUseCase,
    FailPaymentUseCase,
)
from src.domain.payment import Payment, Quote

router = APIRouter(tags=["billing"])


class CreateQuoteRequest(BaseModel):
    service_order_id: str
    items: list[str]
    amount: Decimal


class FailPaymentRequest(BaseModel):
    reason: str


class MercadoPagoWebhookRequest(BaseModel):
    payment_id: str
    status: str
    status_detail: str | None = None


def quote_to_response(quote: Quote) -> dict[str, Any]:
    return {
        "quote_id": quote.quote_id,
        "service_order_id": quote.service_order_id,
        "items": quote.items,
        "amount": str(quote.total.amount),
        "currency": quote.total.currency,
        "status": quote.status.value,
    }


def payment_to_response(payment: Payment) -> dict[str, Any]:
    return {
        "payment_id": payment.payment_id,
        "quote_id": payment.quote_id,
        "service_order_id": payment.service_order_id,
        "amount": str(payment.total.amount),
        "currency": payment.total.currency,
        "status": payment.status.value,
        "preference": None
        if payment.preference is None
        else {
            "preference_id": payment.preference.preference_id,
            "checkout_url": payment.preference.checkout_url,
        },
    }


@router.post("/quotes", status_code=status.HTTP_201_CREATED)
def create_quote(payload: CreateQuoteRequest, request: Request) -> dict[str, Any]:
    use_case = CreateQuoteUseCase(
        request.app.state.quote_repository,
        request.app.state.event_publisher,
    )
    try:
        quote = use_case.execute(
            CreateQuoteCommand(
                service_order_id=payload.service_order_id,
                items=payload.items,
                amount=payload.amount,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return quote_to_response(quote)


@router.get("/quotes/{quote_id}")
def get_quote(quote_id: str, request: Request) -> dict[str, Any]:
    try:
        quote = request.app.state.quote_repository.get(quote_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return quote_to_response(quote)


@router.post("/quotes/{quote_id}/approve")
def approve_quote(quote_id: str, request: Request) -> dict[str, Any]:
    use_case = ApproveQuoteUseCase(
        request.app.state.quote_repository,
        request.app.state.payment_repository,
        request.app.state.event_publisher,
        request.app.state.payment_gateway,
    )
    try:
        payment = use_case.execute(quote_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str, request: Request) -> dict[str, Any]:
    try:
        payment = request.app.state.payment_repository.get(payment_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.post("/payments/{payment_id}/confirm")
def confirm_payment(payment_id: str, request: Request) -> dict[str, Any]:
    try:
        payment = ConfirmPaymentUseCase(
            request.app.state.payment_repository,
            request.app.state.event_publisher,
        ).execute(payment_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.post("/payments/{payment_id}/fail")
def fail_payment(
    payment_id: str,
    payload: FailPaymentRequest,
    request: Request,
) -> dict[str, Any]:
    try:
        payment = FailPaymentUseCase(
            request.app.state.payment_repository,
            request.app.state.event_publisher,
        ).execute(payment_id, payload.reason)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.post("/payments/mercado-pago/webhook")
def handle_mercado_pago_webhook(
    payload: MercadoPagoWebhookRequest,
    request: Request,
) -> dict[str, Any]:
    normalized_status = payload.status.strip().lower()
    try:
        if normalized_status in {"approved", "accredited"}:
            payment = ConfirmPaymentUseCase(
                request.app.state.payment_repository,
                request.app.state.event_publisher,
            ).execute(payload.payment_id)
        elif normalized_status in {
            "rejected",
            "cancelled",
            "refunded",
            "charged_back",
            "expired",
        }:
            payment = FailPaymentUseCase(
                request.app.state.payment_repository,
                request.app.state.event_publisher,
            ).execute(
                payload.payment_id,
                payload.status_detail or f"Mercado Pago status: {payload.status}",
            )
        elif normalized_status in {"pending", "in_process"}:
            payment = request.app.state.payment_repository.get(payload.payment_id)
        else:
            raise ValueError(f"Unsupported Mercado Pago status: {payload.status}")
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return payment_to_response(payment)
