from __future__ import annotations

from fastapi import APIRouter, Depends

from src.domain.auth import AuthenticatedPrincipal
from src.presentation.dependencies.auth import get_current_principal

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/validate")
def validate_token(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, str | None]:
    return {
        "subject": principal.subject,
        "role": principal.role,
        "customer_id": principal.customer_id,
        "issuer": principal.issuer,
    }
