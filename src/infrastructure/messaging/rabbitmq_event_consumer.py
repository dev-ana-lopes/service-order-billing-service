from __future__ import annotations

import json
from typing import Any, Callable

from src.infrastructure.messaging.event_contracts import validate_event_message


class RabbitMqEventConsumer:
    def __init__(self, handler: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._handler = handler

    def handle_message(self, body: bytes) -> dict[str, Any]:
        message = json.loads(body.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("RabbitMQ message body must be an object")
        validate_event_message(message)
        if self._handler is not None:
            self._handler(message)
        return message
