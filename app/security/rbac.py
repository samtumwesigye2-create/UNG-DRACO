from dataclasses import dataclass
from typing import Iterable

from fastapi import Depends, HTTPException, status


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: set[str]


def authorize_roles(principal: Principal, allowed_roles: Iterable[str]) -> None:
    if principal.roles.isdisjoint(set(allowed_roles)):
        raise PermissionError("principal lacks required DRACO role")


def require_roles(*allowed_roles: str):
    from app.security.auth import get_current_principal

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        try:
            authorize_roles(principal, allowed_roles)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden") from exc
        return principal

    return dependency
