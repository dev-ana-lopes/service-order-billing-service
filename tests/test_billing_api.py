from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from src.domain.payment import Money, PaymentGatewayError
from src.infrastructure.config.settings import Settings
from src.main import create_app


def test_app_has_billing_dependencies():
    app = create_app(_settings())

    assert hasattr(app.state, "quote_repository")
    assert hasattr(app.state, "payment_repository")
    assert hasattr(app.state, "event_publisher")
    assert hasattr(app.state, "payment_gateway")


@pytest.mark.asyncio
async def test_billing_api_happy_path():
    settings = _settings()
    app = create_app(settings)
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {_admin_token(settings)}"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        quote_response = await client.post(
            "/quotes",
            json={
                "service_order_id": "os-1",
                "items": ["Brake pads"],
                "amount": str(Decimal("120.00")),
            },
            headers=headers,
        )
        quote_id = quote_response.json()["quote_id"]
        approval_response = await client.post(
            f"/quotes/{quote_id}/approve",
            headers=headers,
        )
        payment_id = approval_response.json()["payment_id"]
        payment_response = await client.get(
            f"/payments/{payment_id}",
            headers=headers,
        )
        confirm_response = await client.post(
            f"/payments/{payment_id}/confirm",
            headers=headers,
        )

    assert quote_response.status_code == 201
    assert quote_response.json()["status"] == "CREATED"
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "PENDING"
    assert (
        approval_response.json()["preference"]["checkout_url"]
        == "https://checkout.local/os-1"
    )
    assert payment_response.status_code == 200
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_mercado_pago_webhook_confirms_payment():
    settings = _settings()
    app = create_app(settings)
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {_admin_token(settings)}"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        quote_response = await client.post(
            "/quotes",
            json={
                "service_order_id": "os-1",
                "items": ["Brake pads"],
                "amount": str(Decimal("120.00")),
            },
            headers=headers,
        )
        quote_id = quote_response.json()["quote_id"]
        approval_response = await client.post(
            f"/quotes/{quote_id}/approve",
            headers=headers,
        )
        payment_id = approval_response.json()["payment_id"]
        webhook_response = await client.post(
            "/payments/mercado-pago/webhook",
            json={"payment_id": payment_id, "status": "approved"},
        )

    assert webhook_response.status_code == 200
    assert webhook_response.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_billing_api_returns_not_found():
    settings = _settings()
    app = create_app(settings)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/quotes/missing",
            headers={"Authorization": f"Bearer {_admin_token(settings)}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_billing_api_returns_bad_gateway_when_payment_provider_fails():
    settings = _settings()
    app = create_app(settings)
    app.state.payment_gateway = FailingPaymentGateway()
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {_admin_token(settings)}"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        quote_response = await client.post(
            "/quotes",
            json={
                "service_order_id": "os-1",
                "items": ["Brake pads"],
                "amount": str(Decimal("120.00")),
            },
            headers=headers,
        )
        quote_id = quote_response.json()["quote_id"]
        approval_response = await client.post(
            f"/quotes/{quote_id}/approve",
            headers=headers,
        )

    assert quote_response.status_code == 201
    assert approval_response.status_code == 502
    assert "MERCADO_PAGO_ACCESS_TOKEN" in approval_response.json()["detail"]


@pytest.mark.asyncio
async def test_billing_api_requires_valid_token():
    settings = _settings()
    app = create_app(settings)
    transport = ASGITransport(app=app)
    invalid_token = jwt.encode(
        {"role": "admin", "user_id": "admin-1"},
        "wrong-secret",
        algorithm="HS256",
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        unauthorized = await client.get("/quotes/missing")
        forbidden = await client.get(
            "/quotes/missing",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

    assert unauthorized.status_code == 401
    assert forbidden.status_code == 403


def _settings() -> Settings:
    return Settings(
        APP_NAME="service-order-billing-service",
        APP_VERSION="0.1.0",
        ENVIRONMENT="test",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        JWT_SECRET="test-secret-value-with-32-characters",
        CUSTOMER_JWT_SECRET="customer-secret-value-with-32-characters",
        CUSTOMER_JWT_ISSUER="service-order-auth-lambda/test",
    )


class FailingPaymentGateway:
    def create_checkout_preference(
        self, quote_id: str, service_order_id: str, total: Money
    ):
        del quote_id, service_order_id, total
        raise PaymentGatewayError(
            "Mercado Pago request failed with status 403. Check whether "
            "MERCADO_PAGO_ACCESS_TOKEN is valid for the configured Mercado Pago environment.",
            status_code=403,
        )


def _admin_token(settings: Settings) -> str:
    return jwt.encode(
        {"role": "admin", "user_id": "admin-1", "iss": settings.JWT_ISSUER},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
