import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.events import DomainEvent
from src.infrastructure.config.settings import Settings
from src.infrastructure.messaging.event_contracts import validate_event_message
from src.main import create_app


def test_event_contract_rejects_invalid_event_type():
    with pytest.raises(ValueError, match="Unsupported event type"):
        validate_event_message(
            {
                "event_id": "event-1",
                "event_type": "UNKNOWN",
                "correlation_id": "os-1",
                "occurred_at": "2026-07-05T00:00:00Z",
                "payload": {},
            }
        )


@pytest.mark.asyncio
async def test_event_api_lists_and_drains_published_messages():
    app = create_app(_settings())
    app.state.event_publisher.publish(
        DomainEvent(
            event_type="QUOTE_CREATED",
            correlation_id="os-1",
            payload={"service_order_id": "os-1", "quote_id": "quote-1"},
        )
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        list_response = await client.get("/events")
        drain_response = await client.post("/events/drain")
        empty_response = await client.get("/events")

    assert list_response.status_code == 200
    assert list_response.json()["events"][0]["event_type"] == "QUOTE_CREATED"
    assert drain_response.json()["events"][0]["event_type"] == "QUOTE_CREATED"
    assert empty_response.json()["events"] == []


def _settings() -> Settings:
    return Settings(
        APP_NAME="service-order-billing-service",
        APP_VERSION="0.1.0",
        ENVIRONMENT="test",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        JWT_SECRET="test-secret-value-with-32-characters",
        APPROVAL_TOKEN_SECRET="approval-secret-value-with-32-chars",
    )
