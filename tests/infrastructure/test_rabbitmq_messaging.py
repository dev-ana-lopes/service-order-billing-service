import json

import pytest

from src.domain.events import DomainEvent
from src.infrastructure.messaging.rabbitmq_event_consumer import RabbitMqEventConsumer
from src.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMqEventPublisher,
    RabbitMqEventPublisherSettings,
)


class FakeRabbitMqChannel:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []

    def basic_publish(
        self,
        exchange: str,
        routing_key: str,
        body: bytes,
        properties: object | None = None,
    ) -> object:
        self.published.append(
            {
                "exchange": exchange,
                "routing_key": routing_key,
                "body": body,
                "properties": properties,
            }
        )
        return None


def test_rabbitmq_publisher_serializes_valid_event_message() -> None:
    channel = FakeRabbitMqChannel()
    publisher = RabbitMqEventPublisher(
        channel,
        RabbitMqEventPublisherSettings(
            exchange="service-order.events",
            routing_key="service-order.billing",
        ),
    )

    publisher.publish(
        DomainEvent(
            event_type="QUOTE_CREATED",
            correlation_id="os-1",
            payload={"quote_id": "quote-1"},
        )
    )

    published = channel.published[0]
    body = json.loads(bytes(published["body"]).decode("utf-8"))
    assert published["exchange"] == "service-order.events"
    assert published["routing_key"] == "service-order.billing"
    assert body["event_type"] == "QUOTE_CREATED"
    assert body["payload"] == {"quote_id": "quote-1"}


def test_rabbitmq_consumer_validates_and_dispatches_message() -> None:
    handled: list[dict[str, object]] = []
    consumer = RabbitMqEventConsumer(lambda message: handled.append(message))
    body = json.dumps(
        {
            "event_id": "event-1",
            "event_type": "PAYMENT_CONFIRMED",
            "correlation_id": "os-1",
            "occurred_at": "2026-07-05T12:00:00+00:00",
            "payload": {"payment_id": "payment-1"},
        }
    ).encode("utf-8")

    message = consumer.handle_message(body)

    assert message["event_type"] == "PAYMENT_CONFIRMED"
    assert handled == [message]


def test_rabbitmq_consumer_rejects_invalid_event_message() -> None:
    consumer = RabbitMqEventConsumer()
    body = json.dumps(
        {
            "event_id": "event-1",
            "event_type": "UNKNOWN",
            "correlation_id": "os-1",
            "occurred_at": "2026-07-05T12:00:00+00:00",
            "payload": {},
        }
    ).encode("utf-8")

    with pytest.raises(ValueError, match="Unsupported event type"):
        consumer.handle_message(body)
