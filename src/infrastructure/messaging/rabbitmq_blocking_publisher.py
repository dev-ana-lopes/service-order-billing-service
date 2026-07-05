from __future__ import annotations

from src.domain.events import DomainEvent
from src.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMqEventPublisher,
    RabbitMqEventPublisherSettings,
)


class RabbitMqBlockingEventPublisher:
    def __init__(self, url: str, exchange: str, routing_key: str, queue: str) -> None:
        import pika

        self._connection = pika.BlockingConnection(pika.URLParameters(url))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            durable=True,
        )
        self._channel.queue_declare(queue=queue, durable=True)
        self._channel.queue_bind(exchange=exchange, queue=queue, routing_key=routing_key)
        self._publisher = RabbitMqEventPublisher(
            self._channel,
            RabbitMqEventPublisherSettings(exchange=exchange, routing_key=routing_key),
        )

    def publish(self, event: DomainEvent) -> None:
        self._publisher.publish(event)

    def close(self) -> None:
        if self._connection.is_open:
            self._connection.close()
