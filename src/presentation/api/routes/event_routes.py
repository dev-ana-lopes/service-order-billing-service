from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def list_published_events(request: Request) -> dict[str, list[dict[str, Any]]]:
    return {"events": request.app.state.event_publisher.published_messages()}


@router.post("/drain")
def drain_published_events(request: Request) -> dict[str, list[dict[str, Any]]]:
    return {"events": request.app.state.event_publisher.drain()}
