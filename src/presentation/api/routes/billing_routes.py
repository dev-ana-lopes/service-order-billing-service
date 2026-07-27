from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from src.application.use_cases import (
    ApplyPaymentStatusCommand,
    ApplyPaymentStatusUseCase,
    ApproveQuoteUseCase,
    ConfirmPaymentUseCase,
    CreateQuoteCommand,
    CreateQuoteUseCase,
    FailPaymentUseCase,
    SyncPaymentStatusUseCase,
)
from src.domain.auth import AuthenticatedPrincipal
from src.domain.payment import Payment, PaymentGatewayError, Quote
from src.infrastructure.observability.metrics import PAYMENT_TRANSITION_COUNTER
from src.presentation.dependencies.auth import require_admin_principal

router = APIRouter(tags=["billing"])


class CreateQuoteRequest(BaseModel):
    service_order_id: str
    items: list[str]
    amount: Decimal


class FailPaymentRequest(BaseModel):
    reason: str


class SimulatePaymentRequest(BaseModel):
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
            "external_reference": payment.preference.external_reference,
        },
    }


@router.post("/quotes", status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: CreateQuoteRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
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
def get_quote(
    quote_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
    try:
        quote = request.app.state.quote_repository.get(quote_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return quote_to_response(quote)


@router.get("/quotes/by-service-order/{service_order_id}")
def get_quote_by_service_order(
    service_order_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
    try:
        quote = request.app.state.quote_repository.get_by_service_order_id(
            service_order_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return quote_to_response(quote)


@router.post("/quotes/{quote_id}/approve")
def approve_quote(
    quote_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
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
    except PaymentGatewayError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
    try:
        payment = request.app.state.payment_repository.get(payment_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.get("/payments/by-service-order/{service_order_id}")
def get_payment_by_service_order(
    service_order_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
    try:
        payment = request.app.state.payment_repository.get_by_service_order_id(
            service_order_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return payment_to_response(payment)


@router.post("/payments/{payment_id}/confirm")
def confirm_payment(
    payment_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
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
    PAYMENT_TRANSITION_COUNTER.labels(result="confirmed").inc()
    return payment_to_response(payment)


@router.post("/payments/{payment_id}/fail")
def fail_payment(
    payment_id: str,
    payload: FailPaymentRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
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
    PAYMENT_TRANSITION_COUNTER.labels(result="failed").inc()
    return payment_to_response(payment)


@router.post("/payments/{payment_id}/sync")
def sync_payment_status(
    payment_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
    try:
        result = SyncPaymentStatusUseCase(
            request.app.state.payment_repository,
            request.app.state.event_publisher,
            request.app.state.payment_gateway,
        ).execute(payment_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PaymentGatewayError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    if result.action == "confirmed":
        PAYMENT_TRANSITION_COUNTER.labels(result="confirmed").inc()
    elif result.action == "failed":
        PAYMENT_TRANSITION_COUNTER.labels(result="failed").inc()
    response = payment_to_response(result.payment)
    response.update(
        {
            "provider_payment_id": result.provider_payment_id,
            "provider_status": result.provider_status,
            "provider_status_detail": result.provider_status_detail,
            "action": result.action,
            "published_event_type": result.published_event_type,
        }
    )
    return response


@router.post("/internal/test/payments/{payment_id}/simulate")
def simulate_payment_update(
    payment_id: str,
    payload: SimulatePaymentRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, Any]:
    del principal
    if not request.app.state.settings.ENABLE_INTERNAL_TEST_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internal test endpoints are disabled.",
        )
    try:
        result = _apply_payment_status(
            request,
            payment_id=payment_id,
            provider_status=payload.status,
            provider_status_detail=payload.status_detail,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    if result["action"] == "confirmed":
        PAYMENT_TRANSITION_COUNTER.labels(result="confirmed").inc()
    elif result["action"] == "failed":
        PAYMENT_TRANSITION_COUNTER.labels(result="failed").inc()
    return result


def _apply_payment_status(
    request: Request,
    *,
    payment_id: str,
    provider_status: str,
    provider_status_detail: str | None,
) -> dict[str, Any]:
    result = ApplyPaymentStatusUseCase(
        request.app.state.payment_repository,
        request.app.state.event_publisher,
    ).execute(
        ApplyPaymentStatusCommand(
            payment_id=payment_id,
            provider_status=provider_status,
            provider_status_detail=provider_status_detail,
        )
    )
    response = payment_to_response(result.payment)
    response.update(
        {"action": result.action, "published_event_type": result.published_event_type}
    )
    return response
