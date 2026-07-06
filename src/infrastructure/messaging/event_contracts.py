from __future__ import annotations

from typing import Any

from src.domain.events import DomainEvent

INTEGRATION_EVENT_TYPES = {
    "OS_OPENED",
    "QUOTE_CREATED",
    "QUOTE_APPROVED",
    "QUOTE_CANCELLED",
    "PAYMENT_PREFERENCE_CREATED",
    "PAYMENT_CONFIRMED",
    "PAYMENT_FAILED",
}


def event_to_message(event: DomainEvent) -> dict[str, Any]:
    message = event.to_message()
    validate_event_message(message)
    return message


def validate_event_message(message: dict[str, Any]) -> None:
    required_fields = {
        "event_id",
        "event_type",
        "correlation_id",
        "occurred_at",
        "payload",
    }
    missing_fields = required_fields - set(message)
    if missing_fields:
        raise ValueError(f"Event message is missing fields: {sorted(missing_fields)}")
    if message["event_type"] not in INTEGRATION_EVENT_TYPES:
        raise ValueError(f"Unsupported event type: {message['event_type']}")
    if not isinstance(message["payload"], dict):
        raise ValueError("Event payload must be an object")
