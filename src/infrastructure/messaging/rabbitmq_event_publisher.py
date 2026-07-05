from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from src.domain.events import DomainEvent
from src.infrastructure.messaging.event_contracts import event_to_message


class RabbitMqChannelPort(Protocol):
    def basic_publish(
        self,
        exchange: str,
        routing_key: str,
        body: bytes,
        properties: object | None = None,
    ) -> object:
        pass


@dataclass(frozen=True)
class RabbitMqEventPublisherSettings:
    exchange: str
    routing_key: str


class RabbitMqEventPublisher:
    def __init__(
        self,
        channel: RabbitMqChannelPort,
        settings: RabbitMqEventPublisherSettings,
    ) -> None:
        self._channel = channel
        self._settings = settings

    def publish(self, event: DomainEvent) -> None:
        message = event_to_message(event)
        body = json.dumps(message, separators=(",", ":")).encode("utf-8")
        self._channel.basic_publish(
            exchange=self._settings.exchange,
            routing_key=self._settings.routing_key,
            body=body,
            properties=None,
        )
