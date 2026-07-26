from __future__ import annotations

from threading import Lock

from src.domain.events import DomainEvent
from src.infrastructure.messaging.event_contracts import event_to_message
from src.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMqEventPublisher,
    RabbitMqEventPublisherSettings,
)


class RabbitMqBlockingEventPublisher:
    def __init__(self, url: str, exchange: str, routing_key: str, queue: str) -> None:
        self._url = url
        self._exchange = exchange
        self._routing_key = routing_key
        self._queue = queue
        self._lock = Lock()
        self._messages: list[dict[str, object]] = []

    def _build_publisher(self) -> tuple[object, RabbitMqEventPublisher]:
        import pika

        connection = pika.BlockingConnection(pika.URLParameters(self._url))
        channel = connection.channel()
        channel.exchange_declare(
            exchange=self._exchange,
            exchange_type="topic",
            durable=True,
        )
        channel.queue_declare(queue=self._queue, durable=True)
        channel.queue_bind(
            exchange=self._exchange,
            queue=self._queue,
            routing_key=self._routing_key,
        )
        publisher = RabbitMqEventPublisher(
            channel,
            RabbitMqEventPublisherSettings(
                exchange=self._exchange,
                routing_key=self._routing_key,
            ),
        )
        return connection, publisher

    def publish(self, event: DomainEvent) -> None:
        # Use a short-lived connection to avoid stale heartbeat timeouts
        # in low-throughput local/demo environments.
        with self._lock:
            connection, publisher = self._build_publisher()
            try:
                publisher.publish(event)
                self._messages.append(event_to_message(event))
            finally:
                if connection.is_open:
                    connection.close()

    def published_messages(self) -> list[dict[str, object]]:
        with self._lock:
            return list(self._messages)

    def drain(self) -> list[dict[str, object]]:
        with self._lock:
            messages = list(self._messages)
            self._messages.clear()
            return messages

    def close(self) -> None:
        return None
