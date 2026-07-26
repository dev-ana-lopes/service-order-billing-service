import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from src.infrastructure.config.settings import Settings
from src.main import create_app


@pytest.mark.asyncio
async def test_auth_validate_accepts_admin_token_with_os_issuer():
    settings = _settings()
    app = create_app(settings)
    transport = ASGITransport(app=app)
    token = jwt.encode(
        {
            "role": "admin",
            "user_id": "admin-1",
            "email": "admin@example.com",
            "iss": settings.JWT_ISSUER,
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["issuer"] == settings.JWT_ISSUER


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
