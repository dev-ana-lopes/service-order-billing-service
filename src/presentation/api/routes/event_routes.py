from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from src.domain.auth import AuthenticatedPrincipal
from src.presentation.dependencies.auth import require_admin_principal

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def list_published_events(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, list[dict[str, Any]]]:
    del principal
    return {"events": request.app.state.event_publisher.published_messages()}


@router.post("/drain")
def drain_published_events(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_admin_principal),
) -> dict[str, list[dict[str, Any]]]:
    del principal
    return {"events": request.app.state.event_publisher.drain()}
