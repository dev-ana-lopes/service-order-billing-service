import json

import pytest

from src.domain.events import DomainEvent
from src.infrastructure.messaging.rabbitmq_blocking_publisher import (
    RabbitMqBlockingEventPublisher,
)
from src.infrastructure.messaging.rabbitmq_event_consumer import RabbitMqEventConsumer
from src.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMqEventPublisher,
    RabbitMqEventPublisherSettings,
)


class FakeRabbitMqChannel:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []
        self.declarations: list[dict[str, object]] = []

    def exchange_declare(
        self,
        exchange: str,
        exchange_type: str,
        durable: bool,
    ) -> None:
        self.declarations.append(
            {
                "kind": "exchange",
                "exchange": exchange,
                "exchange_type": exchange_type,
                "durable": durable,
            }
        )

    def queue_declare(self, queue: str, durable: bool) -> None:
        self.declarations.append(
            {
                "kind": "queue",
                "queue": queue,
                "durable": durable,
            }
        )

    def queue_bind(self, exchange: str, queue: str, routing_key: str) -> None:
        self.declarations.append(
            {
                "kind": "bind",
                "exchange": exchange,
                "queue": queue,
                "routing_key": routing_key,
            }
        )

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


def test_blocking_rabbitmq_publisher_tracks_and_drains_published_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = FakeRabbitMqChannel()
    closed_connections: list[bool] = []

    class FakeConnection:
        def __init__(self) -> None:
            self.is_open = True

        def channel(self) -> FakeRabbitMqChannel:
            return channel

        def close(self) -> None:
            self.is_open = False
            closed_connections.append(True)

    class FakePikaModule:
        @staticmethod
        def URLParameters(url: str) -> str:
            return url

        @staticmethod
        def BlockingConnection(params: str) -> FakeConnection:
            return FakeConnection()

    monkeypatch.setitem(__import__("sys").modules, "pika", FakePikaModule())

    publisher = RabbitMqBlockingEventPublisher(
        url="amqp://guest:guest@localhost:5672/",
        exchange="service-order.events",
        routing_key="service-order.billing",
        queue="service-order.billing",
    )

    publisher.publish(
        DomainEvent(
            event_type="QUOTE_CREATED",
            correlation_id="os-1",
            payload={"quote_id": "quote-1"},
        )
    )

    messages = publisher.published_messages()
    drained_messages = publisher.drain()

    assert channel.published
    assert messages[0]["event_type"] == "QUOTE_CREATED"
    assert drained_messages == messages
    assert publisher.published_messages() == []
    assert closed_connections == [True]


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
