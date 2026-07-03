import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.config.settings import Settings
from src.main import create_app


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints_return_operational_status():
    settings = Settings(
        APP_NAME="service-order-billing-service",
        APP_VERSION="0.1.0",
        ENVIRONMENT="test",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        JWT_SECRET="test-secret-value-with-32-characters",
        APPROVAL_TOKEN_SECRET="approval-secret-value-with-32-chars",
    )
    app = create_app(settings)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        health_response = await client.get("/health")
        readiness_response = await client.get("/health/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
        "service": "service-order-billing-service",
        "version": "0.1.0",
        "environment": "test",
    }
    assert readiness_response.status_code == 200
    assert readiness_response.json()["checks"] == {"application": "ok"}
