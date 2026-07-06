from __future__ import annotations

import json
from typing import Any, Callable

from src.infrastructure.messaging.event_contracts import validate_event_message


class RabbitMqBlockingEventWorker:
    def __init__(
        self,
        url: str,
        exchange: str,
        queue: str,
        routing_keys: list[str],
        handler: Callable[[dict[str, Any]], str],
    ) -> None:
        import pika

        self._queue = queue
        self._connection = pika.BlockingConnection(pika.URLParameters(url))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            durable=True,
        )
        self._channel.queue_declare(queue=queue, durable=True)
        for routing_key in routing_keys:
            self._channel.queue_bind(
                exchange=exchange,
                queue=queue,
                routing_key=routing_key,
            )
        self._handler = handler

    def start(self) -> None:
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(
            queue=self._queue,
            on_message_callback=self._handle_delivery,
        )
        self._channel.start_consuming()

    def _handle_delivery(self, channel, method, properties, body: bytes) -> None:
        try:
            message = json.loads(body.decode("utf-8"))
            if not isinstance(message, dict):
                raise ValueError("RabbitMQ message body must be an object")
            validate_event_message(message)
            self._handler(message)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def close(self) -> None:
        if self._connection.is_open:
            self._connection.close()
