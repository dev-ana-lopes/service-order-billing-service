from __future__ import annotations

from src.domain.events import DomainEvent
from src.infrastructure.messaging.event_contracts import event_to_message


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []
        self.messages: list[dict[str, object]] = []

    def publish(self, event: DomainEvent) -> None:
        self.events.append(event)
        self.messages.append(event_to_message(event))

    def published_messages(self) -> list[dict[str, object]]:
        return list(self.messages)

    def drain(self) -> list[dict[str, object]]:
        messages = self.published_messages()
        self.events.clear()
        self.messages.clear()
        return messages
