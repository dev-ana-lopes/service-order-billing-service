from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

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
    app = create_app(_settings())
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        quote_response = await client.post(
            "/quotes",
            json={
                "service_order_id": "os-1",
                "items": ["Brake pads"],
                "amount": str(Decimal("120.00")),
            },
        )
        quote_id = quote_response.json()["quote_id"]
        approval_response = await client.post(f"/quotes/{quote_id}/approve")
        payment_id = approval_response.json()["payment_id"]
        payment_response = await client.get(f"/payments/{payment_id}")
        confirm_response = await client.post(f"/payments/{payment_id}/confirm")

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
async def test_billing_api_returns_not_found():
    app = create_app(_settings())
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/quotes/missing")

    assert response.status_code == 404


def _settings() -> Settings:
    return Settings(
        APP_NAME="service-order-billing-service",
        APP_VERSION="0.1.0",
        ENVIRONMENT="test",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        JWT_SECRET="test-secret-value-with-32-characters",
        APPROVAL_TOKEN_SECRET="approval-secret-value-with-32-chars",
    )
