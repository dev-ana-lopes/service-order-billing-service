from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    subject: str
    role: str
    customer_id: str | None
    issuer: str | None
    claims: dict[str, Any]

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
